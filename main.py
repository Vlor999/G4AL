"""G4AL – 2D Survival Game (top-down, bot-controlled NPCs).

Run:  python main.py   →  Web UI (Flask + HTML/CSS/JS Canvas)
"""

import os
from pathlib import Path

# Load .env if present (for MISTRAL_API_KEY, ELEVENLABS_API_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass


def main():
    from server import main as serve
    serve()


if __name__ == "__main__":
    main()
