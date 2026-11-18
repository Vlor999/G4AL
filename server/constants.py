from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ENGINE_EXTENSION = "g4al_game_engine"

# Bounds every request body. A push-to-talk WAV (16 kHz mono 16-bit) takes 32 KB/s:
# about two minutes of speech, a minute and a half once base64-encoded.
MAX_REQUEST_BYTES = 4 * 1024 * 1024
# Shorter than a WAV header plus a few samples: nothing was recorded.
MIN_AUDIO_BYTES = 100
