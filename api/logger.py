"""Structured logging for the game pipeline (powered by loguru).

Writes log files under ``logs/`` with timing, cost, and event data for
every Voxtral call (LLM, audio in), every ElevenLabs TTS call, and a
session summary.

Two sinks:
  • ``logs/pipeline_YYYYMMDD_HHMMSS.log`` – human-readable log
  • ``logs/pipeline_YYYYMMDD_HHMMSS.jsonl`` – structured JSON-lines for analysis

The entry point calls ``use_pipeline_sinks`` once, builds one ``PipelineLogger``,
logs ``start_session`` and hands the logger to the adapters. Importing this module
adds no sink and writes no line.
"""

from __future__ import annotations

import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

from loguru import logger

from api.constants import (
    AUDIO_MODEL,
    AUDIO_MODEL_AUDIO_COST_PER_SECOND,
    AUDIO_MODEL_INPUT_COST_PER_TOKEN,
    AUDIO_MODEL_OUTPUT_COST_PER_TOKEN,
    TTS_COST_PER_CHAR,
)

if TYPE_CHECKING:
    from loguru import Record

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def has_event(record: Record) -> bool:
    """Whether a log record names its ``event``: the filter of every pipeline sink."""
    return "event" in record["extra"]


def configure_sinks(log_dir: Path) -> list[int]:
    """Add the pipeline sinks (console, one file pair per session under ``log_dir``);
    returns their handler ids. Other sinks are left as they are."""
    log_dir.mkdir(parents=True, exist_ok=True)
    session_ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    handler_ids = []

    # Console sink – concise colored output
    handler_ids.append(
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[event]: <18}</cyan> | {message}",
            filter=has_event,
        )
    )

    # Human-readable file sink
    handler_ids.append(
        logger.add(
            str(log_dir / f"pipeline_{session_ts}.log"),
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[event]: <18} | {message}",
            filter=has_event,
            rotation="50 MB",
            encoding="utf-8",
        )
    )

    # Structured JSON-lines sink for programmatic analysis
    handler_ids.append(
        logger.add(
            str(log_dir / f"pipeline_{session_ts}.jsonl"),
            level="DEBUG",
            format="{message}",
            serialize=True,
            filter=has_event,
            rotation="50 MB",
            encoding="utf-8",
        )
    )
    return handler_ids


def use_pipeline_sinks(log_dir: Path = LOG_DIR) -> None:
    """Replace loguru's default sink with the pipeline sinks; the entry point calls it once.

    The default stderr sink would print every pipeline record a second time.
    """
    logger.remove()
    configure_sinks(log_dir)


class LoggedOrder(TypedDict):
    """One order of the ``{"orders": [...]}`` answer ``llm_end`` receives."""

    npc_id: int
    npc_name: str
    action: str
    voice_line: str


def _describe_orders(order: dict[str, Any] | None) -> str:
    """``npc→action`` for each order of an ``{"orders": [...]}`` answer, comma-separated."""
    orders: list[LoggedOrder] = order.get("orders", []) if order else []
    if not orders:
        return "no orders"
    return ", ".join(f"{entry['npc_name']}→{entry['action']}" for entry in orders)


class PipelineLogger:
    """Thread-safe structured logger for Voxtral, TTS and session summary events."""

    def __init__(self) -> None:
        # running totals
        self._total_llm_cost = 0.0
        self._total_tts_cost = 0.0
        self._total_llm_time = 0.0
        self._total_tts_time = 0.0
        self._total_tts_chars = 0
        self._tts_call_count = 0
        self._call_count = 0

        # in-flight timers
        self._llm_t0: float | None = None
        self._tts_t0: float | None = None

    def start_session(self) -> None:
        logger.bind(event="session_start").info("Session started")

    # ── LLM events ───────────────────────────────────────────────────────

    def llm_start(self, input_text: str) -> None:
        self._llm_t0 = time.perf_counter()
        logger.bind(event="llm_start", input_text=input_text).info(f'LLM request: "{input_text}"')

    def llm_end(
        self,
        order: dict[str, Any] | None,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        audio_seconds: int = 0,
        model: str = AUDIO_MODEL,
        error: str | None = None,
    ) -> None:
        """Log the end of a Voxtral call. ``cost_usd`` is the token cost plus the cost of
        the ``audio_seconds`` of input audio, logged apart as ``audio_cost_usd``."""
        elapsed = time.perf_counter() - (self._llm_t0 or time.perf_counter())
        audio_cost = audio_seconds * AUDIO_MODEL_AUDIO_COST_PER_SECOND
        cost = (
            prompt_tokens * AUDIO_MODEL_INPUT_COST_PER_TOKEN
            + completion_tokens * AUDIO_MODEL_OUTPUT_COST_PER_TOKEN
            + audio_cost
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
            audio_seconds=audio_seconds,
            elapsed_s=round(elapsed, 3),
            audio_cost_usd=round(audio_cost, 6),
            cost_usd=round(cost, 6),
            error=error,
        )
        if error:
            log.error(f"LLM error: {error} ({elapsed:.2f}s)")
        else:
            log.info(
                f"LLM response: {_describe_orders(order)} | "
                f"tokens={prompt_tokens}+{completion_tokens} | audio={audio_seconds}s | "
                f"elapsed={elapsed:.2f}s | cost=${cost:.4f}"
            )

    # ── TTS events ────────────────────────────────────────────────────────

    def tts_start(self, text: str, npc_name: str, voice_id: str) -> None:
        self._tts_t0 = time.perf_counter()
        logger.bind(
            event="tts_start",
            npc_name=npc_name,
            voice_id=voice_id,
            char_count=len(text),
        ).info(f"TTS request: {npc_name} ({len(text)} chars) voice={voice_id}")

    def tts_end(
        self,
        npc_name: str,
        char_count: int,
        audio_bytes: int = 0,
        tts_latency_ms: int = 0,
        error: str | None = None,
    ) -> None:
        elapsed = time.perf_counter() - (self._tts_t0 or time.perf_counter())
        cost = char_count * TTS_COST_PER_CHAR
        self._total_tts_cost += cost
        self._total_tts_time += elapsed
        self._total_tts_chars += char_count
        self._tts_call_count += 1
        self._tts_t0 = None

        log = logger.bind(
            event="tts_end",
            npc_name=npc_name,
            char_count=char_count,
            audio_bytes=audio_bytes,
            tts_latency_ms=tts_latency_ms,
            elapsed_s=round(elapsed, 3),
            cost_usd=round(cost, 6),
            error=error,
        )
        if error:
            log.error(f"TTS error for {npc_name}: {error} ({elapsed:.2f}s)")
        else:
            log.info(
                f"TTS done: {npc_name} | chars={char_count} (API-reported) | "
                f"audio={audio_bytes}B | latency={tts_latency_ms}ms | "
                f"elapsed={elapsed:.2f}s | cost=${cost:.4f}"
            )

    # ── pipeline round-trip ──────────────────────────────────────────────

    def pipeline_summary(self, order: dict[str, Any] | None) -> None:
        """Log an end-to-end summary for one voice→LLM→TTS cycle."""
        total_time = self._total_llm_time + self._total_tts_time
        total_cost = self._total_llm_cost + self._total_tts_cost

        logger.bind(
            event="pipeline_summary",
            order=order,
            cumulative_calls=self._call_count,
            cumulative_llm_time_s=round(self._total_llm_time, 3),
            cumulative_tts_time_s=round(self._total_tts_time, 3),
            cumulative_total_time_s=round(total_time, 3),
            cumulative_llm_cost_usd=round(self._total_llm_cost, 6),
            cumulative_tts_cost_usd=round(self._total_tts_cost, 6),
            cumulative_total_cost_usd=round(total_cost, 6),
            cumulative_tts_chars=self._total_tts_chars,
            cumulative_tts_calls=self._tts_call_count,
        ).info(
            f"Pipeline #{self._call_count} done | "
            f"total_time={total_time:.2f}s | total_cost=${total_cost:.4f} "
            f"(llm=${self._total_llm_cost:.4f} "
            f"tts=${self._total_tts_cost:.4f})"
        )

    # ── session close ────────────────────────────────────────────────────

    def close(self) -> None:
        total_cost = self._total_llm_cost + self._total_tts_cost
        logger.bind(
            event="session_end",
            total_calls=self._call_count,
            total_llm_cost_usd=round(self._total_llm_cost, 6),
            total_tts_cost_usd=round(self._total_tts_cost, 6),
            total_cost_usd=round(total_cost, 6),
            total_llm_time_s=round(self._total_llm_time, 3),
            total_tts_time_s=round(self._total_tts_time, 3),
            total_tts_chars=self._total_tts_chars,
            total_tts_calls=self._tts_call_count,
        ).info(
            f"Session ended | calls={self._call_count} | "
            f"llm=${self._total_llm_cost:.4f} | "
            f"tts=${self._total_tts_cost:.4f} ({self._total_tts_chars} chars) | "
            f"total=${total_cost:.4f}"
        )
