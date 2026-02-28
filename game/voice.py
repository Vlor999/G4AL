"""Voxtral Realtime push-to-talk transcription (hold G to record)."""

from __future__ import annotations

import asyncio
import os
import threading
from typing import AsyncIterator, Optional

import pyaudio
from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.extra.realtime import UnknownRealtimeEvent
from mistralai.models import (
    AudioFormat,
    RealtimeTranscriptionError,
    RealtimeTranscriptionSessionCreated,
    TranscriptionStreamDone,
    TranscriptionStreamTextDelta,
)

load_dotenv()

# ── constants ────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 480  # 30 ms chunks at 16 kHz
MODEL = "voxtral-mini-transcribe-realtime-2602"


class VoiceTranscriber:
    """Hold-to-talk microphone → Voxtral Realtime transcription.

    * ``start()``  – begin recording + streaming (non-blocking).
    * ``stop()``   – stop recording; blocks briefly until final text is ready.
    * ``result``   – the transcribed text from the last session.
    """

    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY", "")
        self._client = Mistral(api_key=api_key)
        self._audio_format = AudioFormat(encoding="pcm_s16le", sample_rate=SAMPLE_RATE)

        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._result: str = ""

    # ── public API ───────────────────────────────────────────────────────

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def result(self) -> str:
        return self._result

    def start(self):
        """Begin recording from the microphone and streaming to Voxtral."""
        if self._recording:
            return
        self._recording = True
        self._result = ""
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal recording to stop and wait for final transcription."""
        if not self._recording:
            return
        self._recording = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    # ── internals ────────────────────────────────────────────────────────

    def _run_in_thread(self):
        loop = asyncio.new_event_loop()
        self._loop = loop
        try:
            loop.run_until_complete(self._transcribe())
        except Exception as exc:
            print(f"[voice] error: {exc}")
        finally:
            loop.close()
            self._loop = None

    async def _iter_microphone(self) -> AsyncIterator[bytes]:
        """Yield PCM 16-bit mono chunks from the microphone while recording."""
        p = pyaudio.PyAudio()
        chunk_samples = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)

        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=chunk_samples,
        )

        loop = asyncio.get_running_loop()
        try:
            while self._recording:
                data = await loop.run_in_executor(
                    None, stream.read, chunk_samples, False
                )
                yield data
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

    async def _transcribe(self):
        """Stream mic audio to Voxtral Realtime and accumulate text."""
        text_parts: list[str] = []

        try:
            async for event in self._client.audio.realtime.transcribe_stream(
                audio_stream=self._iter_microphone(),
                model=MODEL,
                audio_format=self._audio_format,
            ):
                if isinstance(event, RealtimeTranscriptionSessionCreated):
                    print("[voice] session created – recording…")
                elif isinstance(event, TranscriptionStreamTextDelta):
                    text_parts.append(event.text)
                elif isinstance(event, TranscriptionStreamDone):
                    print("[voice] transcription done.")
                    break
                elif isinstance(event, RealtimeTranscriptionError):
                    print(f"[voice] API error: {event}")
                    break
                elif isinstance(event, UnknownRealtimeEvent):
                    continue
        except Exception as exc:
            print(f"[voice] stream error: {exc}")

        self._result = "".join(text_parts).strip()
