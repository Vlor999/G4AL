"""Structured logging for the game pipeline (powered by loguru).

Writes log files under ``logs/`` with timing, cost, and event data
for every voice transcription and LLM interpretation call.

Two sinks:
  • ``logs/pipeline_YYYYMMDD_HHMMSS.log`` – human-readable log
  • ``logs/pipeline_YYYYMMDD_HHMMSS.jsonl`` – structured JSON-lines for analysis

Usage:
    from api.logger import pipeline_logger
    pipeline_logger.voice_start()
    pipeline_logger.voice_end(text="hello", audio_seconds=2.3)
    pipeline_logger.llm_start(input_text="hello")
    pipeline_logger.llm_end(order={...}, prompt_tokens=120, completion_tokens=45)
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

# ── Pricing (USD per 1 M tokens / per audio-second) ─────────────────────
# Update these when Mistral changes pricing.
# Source: https://docs.mistral.ai/getting-started/pricing/

VOXTRAL_REALTIME_COST_PER_SECOND = 0.015 / 60  # ~$0.015 / minute → per second
LLM_MODEL = "mistral-small-latest"
LLM_INPUT_COST_PER_TOKEN  = 0.1 / 1_000_000   # $0.1 / 1M input tokens
LLM_OUTPUT_COST_PER_TOKEN = 0.3 / 1_000_000   # $0.3 / 1M output tokens

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def _setup_loguru(log_dir: Path) -> str:
    """Configure loguru sinks and return the session timestamp."""
    log_dir.mkdir(parents=True, exist_ok=True)
    session_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Remove default stderr sink to avoid duplicate prints
    logger.remove()

    # Console sink – concise colored output
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[event]: <18}</cyan> | {message}",
        filter=lambda record: "event" in record["extra"],
    )

    # Human-readable file sink
    logger.add(
        str(log_dir / f"pipeline_{session_ts}.log"),
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[event]: <18} | {message}",
        filter=lambda record: "event" in record["extra"],
        rotation="50 MB",
        encoding="utf-8",
    )

    # Structured JSON-lines sink for programmatic analysis
    logger.add(
        str(log_dir / f"pipeline_{session_ts}.jsonl"),
        level="DEBUG",
        format="{message}",
        serialize=True,
        filter=lambda record: "event" in record["extra"],
        rotation="50 MB",
        encoding="utf-8",
    )

    return session_ts


class PipelineLogger:
    """Thread-safe structured logger for voice + LLM pipeline events."""

    def __init__(self, log_dir: Path = LOG_DIR):
        self._session_ts = _setup_loguru(log_dir)

        # running totals
        self._total_voice_cost = 0.0
        self._total_llm_cost = 0.0
        self._total_voice_time = 0.0
        self._total_llm_time = 0.0
        self._call_count = 0

        # in-flight timers
        self._voice_t0: float | None = None
        self._llm_t0: float | None = None

        logger.bind(event="session_start").info("Session started")

    # ── voice events ─────────────────────────────────────────────────────

    def voice_start(self):
        self._voice_t0 = time.perf_counter()
        logger.bind(event="voice_start").info("Microphone recording started")

    def voice_end(
        self,
        text: str,
        audio_seconds: float = 0.0,
        error: str | None = None,
    ):
        elapsed = time.perf_counter() - (self._voice_t0 or time.perf_counter())
        cost = audio_seconds * VOXTRAL_REALTIME_COST_PER_SECOND
        self._total_voice_cost += cost
        self._total_voice_time += elapsed
        self._voice_t0 = None

        log = logger.bind(
            event="voice_end",
            transcription=text,
            audio_seconds=round(audio_seconds, 2),
            elapsed_s=round(elapsed, 3),
            cost_usd=round(cost, 6),
            error=error,
        )
        if error:
            log.error(f"Voice error: {error} ({elapsed:.2f}s)")
        else:
            log.info(
                f"Transcription: \"{text}\" | audio={audio_seconds:.1f}s | "
                f"elapsed={elapsed:.2f}s | cost=${cost:.4f}"
            )

    # ── LLM events ───────────────────────────────────────────────────────

    def llm_start(self, input_text: str):
        self._llm_t0 = time.perf_counter()
        logger.bind(event="llm_start", input_text=input_text).info(
            f"LLM request: \"{input_text}\""
        )

    def llm_end(
        self,
        order: dict | None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: str = LLM_MODEL,
        error: str | None = None,
    ):
        elapsed = time.perf_counter() - (self._llm_t0 or time.perf_counter())
        cost = (
            prompt_tokens * LLM_INPUT_COST_PER_TOKEN
            + completion_tokens * LLM_OUTPUT_COST_PER_TOKEN
        )
        self._total_llm_cost += cost
        self._total_llm_time += elapsed
        self._call_count += 1
        self._llm_t0 = None

        log = logger.bind(
            event="llm_end",
            model=model,
            order=order,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            elapsed_s=round(elapsed, 3),
            cost_usd=round(cost, 6),
            error=error,
        )
        if error:
            log.error(f"LLM error: {error} ({elapsed:.2f}s)")
        else:
            action = order.get("action", "?") if order else "?"
            npc = order.get("npc_name", "?") if order else "?"
            log.info(
                f"LLM response: {npc}→{action} | "
                f"tokens={prompt_tokens}+{completion_tokens} | "
                f"elapsed={elapsed:.2f}s | cost=${cost:.4f}"
            )

    # ── pipeline round-trip ──────────────────────────────────────────────

    def pipeline_summary(self, voice_text: str, order: dict | None):
        """Log an end-to-end summary for one voice→LLM cycle."""
        total_time = self._total_voice_time + self._total_llm_time
        total_cost = self._total_voice_cost + self._total_llm_cost

        logger.bind(
            event="pipeline_summary",
            voice_text=voice_text,
            order=order,
            cumulative_calls=self._call_count,
            cumulative_voice_time_s=round(self._total_voice_time, 3),
            cumulative_llm_time_s=round(self._total_llm_time, 3),
            cumulative_total_time_s=round(total_time, 3),
            cumulative_voice_cost_usd=round(self._total_voice_cost, 6),
            cumulative_llm_cost_usd=round(self._total_llm_cost, 6),
            cumulative_total_cost_usd=round(total_cost, 6),
        ).info(
            f"Pipeline #{self._call_count} done | "
            f"total_time={total_time:.2f}s | total_cost=${total_cost:.4f}"
        )

    # ── session close ────────────────────────────────────────────────────

    def close(self):
        total_cost = self._total_voice_cost + self._total_llm_cost
        logger.bind(
            event="session_end",
            total_calls=self._call_count,
            total_voice_cost_usd=round(self._total_voice_cost, 6),
            total_llm_cost_usd=round(self._total_llm_cost, 6),
            total_cost_usd=round(total_cost, 6),
            total_voice_time_s=round(self._total_voice_time, 3),
            total_llm_time_s=round(self._total_llm_time, 3),
        ).info(
            f"Session ended | calls={self._call_count} | "
            f"voice_cost=${self._total_voice_cost:.4f} | "
            f"llm_cost=${self._total_llm_cost:.4f} | "
            f"total=${total_cost:.4f}"
        )


# ── Singleton ────────────────────────────────────────────────────────────
pipeline_logger = PipelineLogger()
