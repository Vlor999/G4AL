from enum import StrEnum
from pathlib import Path

from api.model_catalog import LlmProvider

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ENGINE_EXTENSION = "g4al_game_engine"

# Bounds every request body. A push-to-talk WAV (16 kHz mono 16-bit) takes 32 KB/s:
# about two minutes of speech, a minute and a half once base64-encoded.
MAX_REQUEST_BYTES = 4 * 1024 * 1024
# Shorter than a WAV header plus a few samples: nothing was recorded.
MIN_AUDIO_BYTES = 100

SERVER_PORT = 8000
# Address the server binds to when G4AL_HOST is not set.
DEFAULT_SERVED_HOST = "127.0.0.1"
# Names a browser on this machine uses to reach a server bound to loopback; the
# startup banner shows the first.
LOOPBACK_HOST_NAMES = ("localhost", "127.0.0.1")
# Wildcard bind addresses: they listen on loopback too, and no browser types them.
# Compared with G4AL_HOST, never bound to here.
WILDCARD_BIND_ADDRESSES = frozenset({"0.0.0.0", "::"})  # noqa: S104
# Bind addresses that listen on loopback.
LOOPBACK_BIND_ADDRESSES = frozenset({"localhost", "127.0.0.1", "::1"}) | WILDCARD_BIND_ADDRESSES


# Longest typed command POST /api/command accepts, in characters: a few sentences.
MAX_COMMAND_CHARACTERS = 500
# Chat messages the state keeps: older ones scroll out of the chat panel.
CHAT_HISTORY_LENGTH = 30


LLM_PROVIDER_VARIABLE = "G4AL_LLM_PROVIDER"
LLM_MODEL_VARIABLE = "G4AL_LLM_MODEL"
DEFAULT_LLM_PROVIDER = LlmProvider.MISTRAL
# The environment variable that holds each provider's API key.
API_KEY_VARIABLES: dict[LlmProvider, str] = {LlmProvider.MISTRAL: "MISTRAL_API_KEY"}


class ChatMessageKind(StrEnum):
    """The ``kind`` of each entry of the state's ``chat`` list (`docs/api.md`)."""

    TYPED_COMMAND = "typed_command"
    SPOKEN_COMMAND = "spoken_command"
    VOICE_LINE = "voice_line"
