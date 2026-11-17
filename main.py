"""G4AL – 2D Survival Game (top-down, bot-controlled NPCs).

Run:  python main.py   →  Web UI (Flask + HTML/CSS/JS Canvas)
"""


def main() -> None:
    from server.app import main as serve

    serve()


if __name__ == "__main__":
    main()
