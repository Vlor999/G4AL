from collections.abc import Iterator

import pytest
from flask.testing import FlaskClient

from server.app import create_app
from server.constants import SERVER_PORT
from server.engine import GameEngine
from tests.fakes import RecordingSpeaker, ScriptedOrderInterpreter


@pytest.fixture
def engine() -> GameEngine:
    """A fresh game engine with fake ports, without the game loop thread."""
    return GameEngine(interpreter=ScriptedOrderInterpreter(), speaker=RecordingSpeaker())


@pytest.fixture
def client(engine: GameEngine) -> Iterator[FlaskClient]:
    """Serve ``engine`` through Flask's test client."""
    app, _ = create_app(engine)
    # The test client sends SERVER_NAME as Host: the address a browser on this machine uses.
    app.config["SERVER_NAME"] = f"localhost:{SERVER_PORT}"
    with app.test_client() as test_client:
        yield test_client
