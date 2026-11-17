import os
from collections.abc import Iterator

import pytest

# The server initialises the pygame mixer at import: use a silent driver so the
# suite runs on machines and CI runners without an audio device.
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flask.testing import FlaskClient

import server

# Importing the server loads `.env`; tests must never reach the paid APIs with a
# developer's real keys.
_API_KEY_VARIABLES = ("MISTRAL_API_KEY", "ELEVENLABS_API_KEY")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[FlaskClient]:
    """Serve a fresh game engine, without the game loop thread, through Flask's test client."""
    for variable in _API_KEY_VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(server, "engine", server.GameEngine())
    with server.app.test_client() as test_client:
        yield test_client
