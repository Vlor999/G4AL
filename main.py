"""G4AL – 2D Survival Game (top-down, bot-controlled NPCs).

Launch modes:
    python main.py          → Web UI (Flask + HTML/CSS/JS Canvas)
    python main.py --pygame  → Legacy Pygame window
"""

import os
import sys
from pathlib import Path

# Load .env if present (for MISTRAL_API_KEY, ELEVENLABS_API_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass


def main():
    if "--pygame" in sys.argv:
        from game.game import Game
        game = Game()
        game.run()
    else:
        from server import main as serve
        serve()


if __name__ == "__main__":
    main()
