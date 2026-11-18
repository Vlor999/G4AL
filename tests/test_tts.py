"""TTSEngine with a fake ElevenLabs client and a fake playback: no API key, no audio device."""

import threading
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast

import pytest
from elevenlabs import ElevenLabs
from loguru import logger

from api.logger import has_event
from api.roster import NPC_VOICE_MAP
from api.tts import TTSEngine

WAIT_SECONDS = 2.0
CLIP = b"ID3-mp3-audio"
API_KEY = "test-key"


class RawSpeechResponse:
    """The context manager ``with_raw_response.convert`` returns."""

    def __init__(self, audio: bytes, headers: dict[str, str]) -> None:
        self.response = SimpleNamespace(headers=headers, data=[audio[:3], audio[3:]])

    def __enter__(self) -> SimpleNamespace:
        return self.response

    def __exit__(self, *exc_info: object) -> None:
        return None


class FakeTextToSpeech:
    """Answers each ``convert`` call with the next clip, or raises it when it is an error."""

    def __init__(self, answers: list[bytes | Exception]) -> None:
        self.answers = answers
        self.calls: list[dict[str, Any]] = []
        self.with_raw_response = self

    def convert(self, **kwargs: Any) -> RawSpeechResponse:
        self.calls.append(kwargs)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return RawSpeechResponse(answer, {"character-cost": "42", "tts-latency-ms": "120"})


class RecordingPlayback:
    """Records each clip played; ``finished`` is set once ``expected_clips`` were played."""

    def __init__(self, expected_clips: int = 1) -> None:
        self.clips: list[bytes] = []
        self.expected_clips = expected_clips
        self.finished = threading.Event()

    def __call__(self, audio: bytes) -> None:
        self.clips.append(audio)
        if len(self.clips) >= self.expected_clips:
            self.finished.set()


class ClientFactory:
    """Records the API keys it is called with; returns ``client`` or raises ``error``."""

    def __init__(self, client: ElevenLabs | None = None, error: Exception | None = None) -> None:
        self.client = client
        self.error = error
        self.api_keys: list[str] = []

    def __call__(self, api_key: str) -> ElevenLabs:
        self.api_keys.append(api_key)
        if self.error is not None:
            raise self.error
        assert self.client is not None
        return self.client


@pytest.fixture
def api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("ELEVENLABS_API_KEY", API_KEY)
    return API_KEY


def speaker_answering(
    answers: list[bytes | Exception], playback: RecordingPlayback
) -> tuple[TTSEngine, FakeTextToSpeech]:
    text_to_speech = FakeTextToSpeech(answers)
    client = cast(ElevenLabs, SimpleNamespace(text_to_speech=text_to_speech))
    speaker = TTSEngine(create_client=ClientFactory(client), play_audio=playback)
    return speaker, text_to_speech


@pytest.fixture
def tts_end_events() -> Iterator[list[dict[str, Any]]]:
    """The ``extra`` fields of every ``tts_end`` log record emitted during the test."""
    events: list[dict[str, Any]] = []
    handler_id = logger.add(
        lambda message: events.append(message.record["extra"]),
        filter=lambda record: record["extra"].get("event") == "tts_end",
    )
    yield events
    logger.remove(handler_id)


@pytest.fixture
def log_lines() -> Iterator[list[tuple[str, str]]]:
    """The level and message of every record that passes the pipeline sinks' filter."""
    lines: list[tuple[str, str]] = []
    handler_id = logger.add(
        lambda message: lines.append((message.record["level"].name, message.record["message"])),
        filter=has_event,
    )
    yield lines
    logger.remove(handler_id)


def test_a_voice_line_is_synthesized_in_the_npc_voice_and_played(
    api_key: str, tts_end_events: list[dict[str, Any]]
) -> None:
    npc_name, voice = next(iter(NPC_VOICE_MAP.items()))
    playback = RecordingPlayback()
    speaker, text_to_speech = speaker_answering([CLIP], playback)

    speaker.speak("On my way!", npc_name)

    assert playback.finished.wait(WAIT_SECONDS)
    speaker.close()
    assert playback.clips == [CLIP]
    [call] = text_to_speech.calls
    assert (call["voice_id"], call["text"]) == (voice, "On my way!")
    [event] = tts_end_events
    assert (event["char_count"], event["audio_bytes"], event["error"]) == (42, len(CLIP), None)


def test_a_failed_line_is_logged_and_the_next_one_still_plays(
    api_key: str, tts_end_events: list[dict[str, Any]]
) -> None:
    playback = RecordingPlayback()
    speaker, _ = speaker_answering([RuntimeError("quota exceeded"), CLIP], playback)

    speaker.speak("First", "Unknown")
    speaker.speak("Second", "Unknown")

    assert playback.finished.wait(WAIT_SECONDS)
    speaker.close()
    assert playback.clips == [CLIP]
    assert [event["error"] for event in tts_end_events] == ["quota exceeded", None]


class FailingFirstPlayback(RecordingPlayback):
    """Raises ``error`` on the first clip, then records the next ones."""

    has_failed = False
    error = RuntimeError("no audio device")

    def __call__(self, audio: bytes) -> None:
        if not self.has_failed:
            self.has_failed = True
            raise self.error
        super().__call__(audio)


def test_a_failed_playback_logs_one_tts_end_and_a_playback_error(
    api_key: str, tts_end_events: list[dict[str, Any]], log_lines: list[tuple[str, str]]
) -> None:
    playback = FailingFirstPlayback()
    speaker, _ = speaker_answering([CLIP, CLIP], playback)

    speaker.speak("First", "Unknown")
    speaker.speak("Second", "Unknown")

    assert playback.finished.wait(WAIT_SECONDS)
    speaker.close()
    assert [(event["char_count"], event["error"]) for event in tts_end_events] == [
        (42, None),
        (42, None),
    ]
    assert ("ERROR", "Playback failed for Unknown: no audio device") in log_lines


def test_a_blank_line_is_never_synthesized(api_key: str) -> None:
    playback = RecordingPlayback()
    speaker, text_to_speech = speaker_answering([CLIP], playback)

    speaker.speak("   ", "Unknown")
    speaker.speak("Hello", "Unknown")

    assert playback.finished.wait(WAIT_SECONDS)
    speaker.close()
    assert [call["text"] for call in text_to_speech.calls] == ["Hello"]


def test_without_an_api_key_no_client_is_built_and_tts_is_disabled(
    monkeypatch: pytest.MonkeyPatch, log_lines: list[tuple[str, str]]
) -> None:
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    create_client = ClientFactory()
    playback = RecordingPlayback()
    speaker = TTSEngine(create_client=create_client, play_audio=playback)

    speaker.speak("Hello", "Unknown")
    speaker.close()

    assert create_client.api_keys == []
    assert ("WARNING", "No ELEVENLABS_API_KEY – TTS disabled") in log_lines
    assert playback.clips == []


def test_a_client_that_fails_to_build_disables_tts(
    api_key: str, log_lines: list[tuple[str, str]]
) -> None:
    create_client = ClientFactory(error=ValueError("bad key"))
    playback = RecordingPlayback()
    speaker = TTSEngine(create_client=create_client, play_audio=playback)

    speaker.speak("Hello", "Unknown")
    speaker.close()

    assert create_client.api_keys == [api_key]
    assert ("ERROR", "Failed to init ElevenLabs client: bad key") in log_lines
    assert playback.clips == []


@pytest.mark.parametrize("configured_key", [API_KEY, f" {API_KEY}\n"])
def test_a_client_build_error_masks_the_api_key(
    monkeypatch: pytest.MonkeyPatch, log_lines: list[tuple[str, str]], configured_key: str
) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", configured_key)
    create_client = ClientFactory(error=ValueError(f"invalid key {API_KEY}"))

    TTSEngine(create_client=create_client, play_audio=RecordingPlayback()).close()

    assert ("ERROR", "Failed to init ElevenLabs client: invalid key <ELEVENLABS_API_KEY>") in (
        log_lines
    )
    assert not any(API_KEY in message for _, message in log_lines)


def test_a_failed_line_masks_the_api_key(
    api_key: str, tts_end_events: list[dict[str, Any]]
) -> None:
    playback = RecordingPlayback()
    speaker, _ = speaker_answering([RuntimeError(f"401 for key {api_key}"), CLIP], playback)

    speaker.speak("First", "Unknown")
    speaker.speak("Second", "Unknown")

    assert playback.finished.wait(WAIT_SECONDS)
    speaker.close()
    assert [event["error"] for event in tts_end_events] == [
        "401 for key <ELEVENLABS_API_KEY>",
        None,
    ]


def test_a_failed_playback_masks_the_api_key(
    api_key: str, log_lines: list[tuple[str, str]]
) -> None:
    playback = FailingFirstPlayback()
    playback.error = RuntimeError(f"device bound to {api_key}")
    speaker, _ = speaker_answering([CLIP, CLIP], playback)

    speaker.speak("First", "Unknown")
    speaker.speak("Second", "Unknown")

    assert playback.finished.wait(WAIT_SECONDS)
    speaker.close()
    assert ("ERROR", "Playback failed for Unknown: device bound to <ELEVENLABS_API_KEY>") in (
        log_lines
    )
    assert not any(api_key in message for _, message in log_lines)
