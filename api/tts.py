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
from collections.abc import Callable
from typing import TYPE_CHECKING

from loguru import logger

from api.constants import ELEVENLABS_API_KEY_MASK
from api.logger import pipeline_logger
from api.roster import NPC_VOICE_MAP, ElevenLabsVoice

if TYPE_CHECKING:
    from elevenlabs import ElevenLabs

# Default fallback voice ID
_DEFAULT_VOICE_ID = ElevenLabsVoice.RACHEL.value

# Model for short voice lines – optimised for low latency.
_MODEL_ID = "eleven_turbo_v2_5"


# ── TTSEngine ────────────────────────────────────────────────────────────


class TTSEngine:
    """``VoiceLineSpeaker`` backed by ElevenLabs and the pygame mixer.

    ``speak`` returns at once and the line plays in the background. ``create_client``
    builds the ElevenLabs client from ``ELEVENLABS_API_KEY``; without that key, or when
    it raises, every line is dropped silently. ``play_audio`` plays one mp3 clip and
    blocks until it ends (default: the pygame mixer, initialised by the entry point).
    """

    def __init__(
        self,
        *,
        create_client: Callable[[str], ElevenLabs] | None = None,
        play_audio: Callable[[bytes], None] | None = None,
    ) -> None:
        self._queue: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self._play_audio = play_audio or _play_through_mixer
        self._running = True
        self._api_key = os.getenv("ELEVENLABS_API_KEY", "")
        self._client = _build_client(self._api_key, create_client or _create_elevenlabs_client)
        if self._client is None:
            return

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ── public API ───────────────────────────────────────────────────────

    def speak(self, voice_line: str, npc_name: str) -> None:
        """Enqueue a voice line for background playback."""
        if self._client is None or not voice_line.strip():
            return
        self._queue.put((voice_line, npc_name))

    def close(self) -> None:
        """Gracefully stop the worker thread."""
        self._running = False
        self._queue.put(None)  # sentinel

    # ── internals ────────────────────────────────────────────────────────

    def _voice_id_for(self, npc_name: str) -> str:
        """Get the ElevenLabs voice ID for an NPC name."""
        return NPC_VOICE_MAP.get(npc_name, _DEFAULT_VOICE_ID)

    def _worker(self) -> None:
        """Background loop: generate TTS audio and play it with ``play_audio``."""
        if self._client is None:
            return
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

                self._play_audio(audio_bytes)

            except Exception as exc:  # noqa: BLE001 - worker thread must survive any API or playback error
                pipeline_logger.tts_end(
                    npc_name=npc_name,
                    char_count=len(text),
                    error=mask_api_key(str(exc), self._api_key),
                )


def mask_api_key(text: str, api_key: str) -> str:
    """``text`` with ``api_key``, as given and stripped, replaced by a mask.

    Covers only these two plain forms: an encoded key (URL, base64) stays as it is.
    """
    for secret in (api_key, api_key.strip()):
        if secret:
            text = text.replace(secret, ELEVENLABS_API_KEY_MASK)
    return text


def _build_client(api_key: str, create_client: Callable[[str], ElevenLabs]) -> ElevenLabs | None:
    """Build the client from ``api_key``; None, logged, when it cannot."""
    log = logger.bind(event="tts_disabled")
    if not api_key:
        log.warning("No ELEVENLABS_API_KEY – TTS disabled")
        return None

    try:
        return create_client(api_key)
    except Exception as exc:  # noqa: BLE001 - client init failure disables TTS instead of crashing
        log.error(f"Failed to init ElevenLabs client: {mask_api_key(str(exc), api_key)}")
        return None


def _create_elevenlabs_client(api_key: str) -> ElevenLabs:
    from elevenlabs import ElevenLabs

    return ElevenLabs(api_key=api_key)


def _play_through_mixer(audio_bytes: bytes) -> None:
    import pygame.mixer  # already initialised by the entry point

    # Play through pygame.mixer.music (supports mp3 via SDL_mixer)
    buf = io.BytesIO(audio_bytes)
    pygame.mixer.music.load(buf)
    pygame.mixer.music.play()

    # Block until playback finishes so lines don't overlap
    while pygame.mixer.music.get_busy():
        pygame.time.wait(50)
