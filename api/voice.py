"""Push-to-talk microphone recorder (hold G to record).

Records PCM audio from the microphone while the key is held, then
packages it as an in-memory WAV and hands it to the interpreter for a
single Voxtral multimodal call (audio + text → structured NPC order).
"""

from __future__ import annotations

import base64
import io
import threading
import wave
from typing import Callable, Optional

import pyaudio
from dotenv import load_dotenv

from api.logger import pipeline_logger

load_dotenv()

# ── Audio constants ──────────────────────────────────────────────────────
SAMPLE_RATE = 16_000  # 16 kHz mono
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
CHUNK_SAMPLES = 1024  # frames per read (~64 ms at 16 kHz)


def _pcm_to_wav(pcm_chunks: list[bytes]) -> bytes:
    """Wrap raw PCM 16-bit mono data into a WAV byte string."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        for chunk in pcm_chunks:
            wf.writeframes(chunk)
    return buf.getvalue()


def audio_to_base64(wav_bytes: bytes) -> str:
    """Base64-encode WAV bytes for the Voxtral multimodal API."""
    return base64.b64encode(wav_bytes).decode("utf-8")


class VoiceRecorder:
    """Hold-to-talk microphone recorder.

    * ``start()``  – begin recording (non-blocking).
    * ``stop()``   – stop recording; the background thread will
                     call *on_audio* with the WAV bytes when ready.
    """

    def __init__(self, on_audio: Optional[Callable[[bytes], None]] = None):
        self._on_audio = on_audio
        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._chunks: list[bytes] = []

    # ── public API ───────────────────────────────────────────────────────

    @property
    def recording(self) -> bool:
        return self._recording

    def start(self):
        """Begin capturing mic audio in a background thread."""
        if self._recording:
            return
        self._recording = True
        self._chunks = []
        pipeline_logger.voice_start()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal recording to end. The bg thread finishes and fires on_audio."""
        if not self._recording:
            return
        self._recording = False
        # Don't join — the callback fires from the bg thread when ready.

    # ── internals ────────────────────────────────────────────────────────

    def _record_loop(self):
        """Capture PCM from the mic, convert to WAV, and invoke the callback."""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SAMPLES,
        )

        error_msg: str | None = None
        try:
            while self._recording:
                data = stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
                self._chunks.append(data)
        except Exception as exc:
            error_msg = str(exc)
            print(f"[voice] recording error: {exc}")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

        if not self._chunks:
            pipeline_logger.voice_end(
                text="", audio_seconds=0.0, error=error_msg or "no audio captured"
            )
            return

        # Compute duration from raw PCM data
        total_bytes = sum(len(c) for c in self._chunks)
        audio_seconds = total_bytes / (SAMPLE_RATE * CHANNELS * SAMPLE_WIDTH)

        wav_bytes = _pcm_to_wav(self._chunks)
        self._chunks = []  # free memory

        print(
            f"[voice] recording done ({audio_seconds:.1f}s, {len(wav_bytes)} bytes WAV)"
        )
        pipeline_logger.voice_end(
            text="(audio captured)", audio_seconds=audio_seconds, error=error_msg
        )

        if self._on_audio:
            self._on_audio(wav_bytes)
