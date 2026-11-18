from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ENGINE_EXTENSION = "g4al_game_engine"

# Shorter than a WAV header plus a few samples: nothing was recorded.
MIN_AUDIO_BYTES = 100
