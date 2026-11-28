"""G4AL, a voice-controlled top-down survival game.

Run ``make run`` (or ``uv run python main.py``) and open the URL it prints.
"""


def main() -> None:
    from server.app import main as serve

    serve()


if __name__ == "__main__":
    main()
