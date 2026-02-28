"""Voxtral Realtime push-to-talk transcription (hold G to record)."""

from __future__ import annotations

import asyncio
import os
import threading
from typing import AsyncIterator, Callable, Optional

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

from api.logger import pipeline_logger

load_dotenv()

# ── constants ────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 480  # 30 ms chunks at 16 kHz
SILENCE_FLUSH_MS = 1500   # silence appended after mic stops so server can flush
MODEL = "voxtral-mini-transcribe-realtime-2602"


class VoiceTranscriber:
    """Hold-to-talk microphone → Voxtral Realtime transcription.

    * ``start()``  – begin recording + streaming (non-blocking).
    * ``stop()``   – stop recording; blocks briefly until final text is ready.
    * ``result``   – the transcribed text from the last session.
    """

    def __init__(self, on_result: Optional[Callable[[str], None]] = None):
        api_key = os.getenv("MISTRAL_API_KEY", "")
        self._client = Mistral(api_key=api_key)
        self._audio_format = AudioFormat(encoding="pcm_s16le", sample_rate=SAMPLE_RATE)

        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._result: str = ""
        self._on_result = on_result  # called from bg thread when transcription is ready

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
        self._audio_seconds: float = 0.0
        self._voice_error: str | None = None
        pipeline_logger.voice_start()
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal recording to stop. The background thread will flush remaining
        audio and deliver the result via the on_result callback."""
        if not self._recording:
            return
        self._recording = False
        # Don't join here – let the thread finish flushing in the background.
        # The callback will fire when the result is ready.

    # ── internals ────────────────────────────────────────────────────────

    def _run_in_thread(self):
        loop = asyncio.new_event_loop()
        self._loop = loop
        try:
            loop.run_until_complete(self._transcribe())
        except Exception as exc:
            self._voice_error = str(exc)
            print(f"[voice] error: {exc}")
        finally:
            pipeline_logger.voice_end(
                text=self._result,
                audio_seconds=self._audio_seconds,
                error=self._voice_error,
            )
            loop.close()
            self._loop = None
            self._thread = None
            if self._result and self._on_result:
                self._on_result(self._result)

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
            # After mic stops, send silence so the server can flush its buffer
            silence = b"\x00" * (chunk_samples * 2)  # 16-bit = 2 bytes/sample
            remaining_ms = SILENCE_FLUSH_MS
            while remaining_ms > 0:
                yield silence
                await asyncio.sleep(CHUNK_DURATION_MS / 1000)
                remaining_ms -= CHUNK_DURATION_MS
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
                    # Extract API-reported usage (audio seconds, tokens)
                    if event.usage:
                        self._audio_seconds = float(event.usage.prompt_audio_seconds or 0)
                    print(f"[voice] transcription done (audio={self._audio_seconds:.1f}s).")
                    break
                elif isinstance(event, RealtimeTranscriptionError):
                    print(f"[voice] API error: {event}")
                    break
                elif isinstance(event, UnknownRealtimeEvent):
                    continue
        except Exception as exc:
            print(f"[voice] stream error: {exc}")

        self._result = "".join(text_parts).strip()
