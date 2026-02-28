"""G4AL – 2D Survival Game (top-down, bot-controlled NPCs)."""

import os  # noqa: F401 – used by dotenv side-effects
from pathlib import Path

# Load .env if present (for MISTRAL_API_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from game.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
