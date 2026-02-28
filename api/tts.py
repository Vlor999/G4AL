"""ElevenLabs TTS – speaks NPC voice lines in the background.

Voice assignments come from :pymod:`api.roster` (the single source of
truth for NPC identities).  A daemon worker thread processes a FIFO queue
so voice lines never overlap and never block the game loop.
"""

from __future__ import annotations

import io
import os
import queue
import threading

from dotenv import load_dotenv

from api.logger import pipeline_logger
from api.roster import NPC_VOICE_MAP, ElevenLabsVoice

load_dotenv()

_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Default fallback voice ID
_DEFAULT_VOICE_ID = ElevenLabsVoice.RACHEL.value

# Model for short voice lines – optimised for low latency.
_MODEL_ID = "eleven_turbo_v2_5"


# ── TTSEngine ────────────────────────────────────────────────────────────

class TTSEngine:
    """Non-blocking TTS: call ``speak()`` and audio plays in the background."""

    def __init__(self) -> None:
        self._queue: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self._client = None
        self._running = True

        if not _API_KEY:
            from loguru import logger as _log
            _log.warning("No ELEVENLABS_API_KEY – TTS disabled")
            return

        try:
            from elevenlabs import ElevenLabs
            self._client = ElevenLabs(api_key=_API_KEY)
        except Exception as exc:
            from loguru import logger as _log
            _log.error(f"Failed to init ElevenLabs client: {exc}")
            return

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ── public API ───────────────────────────────────────────────────────

    def speak(self, text: str, npc_name: str = "") -> None:
        """Enqueue a voice line for background playback."""
        if self._client is None or not text.strip():
            return
        self._queue.put((text, npc_name))

    def close(self) -> None:
        """Gracefully stop the worker thread."""
        self._running = False
        self._queue.put(None)  # sentinel

    # ── internals ────────────────────────────────────────────────────────

    def _voice_id_for(self, npc_name: str) -> str:
        """Get the ElevenLabs voice ID for an NPC name."""
        return NPC_VOICE_MAP.get(npc_name, _DEFAULT_VOICE_ID)

    def _worker(self) -> None:
        """Background loop: generate TTS audio and play via pygame.mixer."""
        import pygame.mixer  # already initialised by Game.__init__

        assert self._client is not None
        while self._running:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                break

            text, npc_name = item
            voice_id = self._voice_id_for(npc_name)

            try:
                pipeline_logger.tts_start(text, npc_name, voice_id)

                # Use with_raw_response to access API-reported usage headers
                raw_resp = self._client.text_to_speech.with_raw_response.convert(
                    voice_id=voice_id,
                    text=text,
                    model_id=_MODEL_ID,
                    output_format="mp3_22050_32",
                )
                with raw_resp as http_resp:
                    headers = http_resp.headers
                    character_cost = int(headers.get("character-cost", 0))
                    tts_latency_ms = int(headers.get("tts-latency-ms", 0))
                    audio_bytes = b"".join(http_resp.data)

                pipeline_logger.tts_end(
                    npc_name=npc_name,
                    char_count=character_cost,
                    audio_bytes=len(audio_bytes),
                    tts_latency_ms=tts_latency_ms,
                )

                # Play through pygame.mixer.music (supports mp3 via SDL_mixer)
                buf = io.BytesIO(audio_bytes)
                pygame.mixer.music.load(buf)
                pygame.mixer.music.play()

                # Block until playback finishes so lines don't overlap
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(50)

            except Exception as exc:
                pipeline_logger.tts_end(
                    npc_name=npc_name,
                    char_count=len(text),
                    error=str(exc),
                )
