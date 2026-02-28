"""ElevenLabs TTS – speaks NPC voice lines in the background.

Each NPC name is mapped to a specific ElevenLabs preset voice to match
their personality.  A single daemon worker thread processes a FIFO queue
so voice lines never overlap and never block the game loop.
"""

from __future__ import annotations

import io
import os
import queue
import threading

from dotenv import load_dotenv

from api.logger import pipeline_logger

load_dotenv()

_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# ── ElevenLabs preset voice IDs ─────────────────────────────────────────
# Subset of the default voice library – enough variety for 26 NPCs.

_VOICES: dict[str, str] = {
    # Female
    "Rachel":  "21m00Tcm4TlvDq8ikWAM",  # calm, mature
    "Domi":    "AZnzlk1XvdvUeBnXmlld",  # strong, confident
    "Bella":   "EXAVITQu4vr4xnSDxMaL",  # soft, warm
    "Elli":    "MF3mGyEYCl7XYWbV9V6O",  # young, cheerful
    # Male
    "Josh":    "TxGEqnHWrfWFTfGW9XjX",  # deep, authoritative
    "Arnold":  "VR6AewLTigWG4xSOukaG",  # crisp, military
    "Adam":    "pNInz6obpgDQGcFmaJgB",  # deep, resonant
    "Sam":     "yoZ06aMxZJJ28mfd3POQ",  # raspy, older
    "Antoni":  "ErXwobaYiN019PkySvjV",  # warm, young male
}

_DEFAULT_VOICE = "Rachel"

# ── NPC → ElevenLabs voice mapping ──────────────────────────────────────
# Chosen to loosely match each character's personality / gender.

NPC_VOICE_MAP: dict[str, str] = {
    "Ada":    "Rachel",   # calm, precise thinker
    "Bjorn":  "Josh",     # gruff warrior
    "Cleo":   "Domi",     # sarcastic rogue
    "Dante":  "Adam",     # dramatic poet
    "Elara":  "Bella",    # gentle healer
    "Finn":   "Antoni",   # energetic youngster
    "Greta":  "Domi",     # stern foreman
    "Hugo":   "Sam",      # lazy philosopher
    "Iris":   "Elli",     # cheerful botanist
    "Jasper": "Sam",      # old miner
    "Kira":   "Domi",     # competitive overachiever
    "Ludo":   "Josh",     # gentle giant
    "Mira":   "Rachel",   # pragmatic merchant
    "Niko":   "Antoni",   # rebellious teen
    "Olga":   "Bella",    # grandmother figure
    "Pavel":  "Arnold",   # military engineer
    "Quinn":  "Elli",     # mysterious loner
    "Rolf":   "Adam",     # boisterous bard
    "Suki":   "Rachel",   # cunning strategist
    "Tomas":  "Arnold",   # grumpy worker
    "Uma":    "Bella",    # spiritual mystic
    "Viktor": "Arnold",   # perfectionist
    "Wren":   "Elli",     # shy introvert
    "Xena":   "Domi",     # fierce warrior
    "Yara":   "Bella",    # storyteller
    "Zeke":   "Antoni",   # mad inventor
}

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
        voice_name = NPC_VOICE_MAP.get(npc_name, _DEFAULT_VOICE)
        return _VOICES.get(voice_name, _VOICES[_DEFAULT_VOICE])

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
