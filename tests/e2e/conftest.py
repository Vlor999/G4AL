import os
from collections.abc import Iterator

import pytest

# The server initialises the pygame mixer at import: use a silent driver so the
# suite runs on machines and CI runners without an audio device.
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from flask.testing import FlaskClient

import server
from tests.fakes import RecordingSpeaker, ScriptedOrderInterpreter


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[FlaskClient]:
    """Serve a fresh game engine, without the game loop thread, through Flask's test client."""
    engine = server.GameEngine(interpreter=ScriptedOrderInterpreter(), speaker=RecordingSpeaker())
    monkeypatch.setattr(server, "engine", engine)
    with server.app.test_client() as test_client:
        yield test_client
