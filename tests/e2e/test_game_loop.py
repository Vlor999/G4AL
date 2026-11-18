"""Drive GameEngine's tick and game loop with fake ports and a fake socket emitter."""

from collections.abc import Iterator
from typing import Any, cast

import pytest
from flask_socketio import SocketIO
from loguru import logger

from game.creatures import Arrow
from game.entities import WheatField
from server.engine import GameEngine


def make_arrow(*, frame: int, total_frames: int) -> Arrow:
    return {
        "fromX": 0.0,
        "fromY": 0.0,
        "toX": 10.0,
        "toY": 10.0,
        "frame": frame,
        "totalFrames": total_frames,
        "team": "blue",
    }


class StoppingSocket:
    """Records each state push and stops ``engine`` on push ``stop_at_push``.

    The first ``failing_pushes`` pushes raise, as a dropped connection does.
    """

    def __init__(self, engine: GameEngine, *, stop_at_push: int, failing_pushes: int = 0) -> None:
        self.engine = engine
        self.stop_at_push = stop_at_push
        self.failing_pushes = failing_pushes
        self.pushes: list[dict[str, Any]] = []

    def emit(self, event: str, data: dict[str, Any], namespace: str) -> None:
        assert (event, namespace) == ("state", "/")
        self.pushes.append(data)
        if len(self.pushes) >= self.stop_at_push:
            self.engine.stop()
        if len(self.pushes) <= self.failing_pushes:
            raise ConnectionError("client gone")


@pytest.fixture
def state_push_events() -> Iterator[list[str]]:
    """The level of every ``state_push`` log record emitted during the test."""
    levels: list[str] = []
    handler_id = logger.add(
        lambda message: levels.append(message.record["level"].name),
        filter=lambda record: record["extra"].get("event") == "state_push",
    )
    yield levels
    logger.remove(handler_id)


def run_loop_with(engine: GameEngine, socket: StoppingSocket) -> None:
    engine.run_loop(cast(SocketIO, socket))


def test_the_loop_ticks_and_pushes_the_state_every_third_tick(engine: GameEngine) -> None:
    engine.arrows.append(make_arrow(frame=0, total_frames=1000))
    socket = StoppingSocket(engine, stop_at_push=2)

    run_loop_with(engine, socket)

    assert engine.arrows[0]["frame"] == 6
    assert [len(push["arrows"]) for push in socket.pushes] == [1, 1]


def test_a_failing_push_is_logged_once_per_streak_and_the_loop_keeps_running(
    engine: GameEngine, state_push_events: list[str]
) -> None:
    socket = StoppingSocket(engine, stop_at_push=3, failing_pushes=2)

    run_loop_with(engine, socket)

    assert len(socket.pushes) == 3
    assert state_push_events == ["WARNING", "INFO"]


def test_tick_ages_arrows_and_drops_the_ones_that_landed(engine: GameEngine) -> None:
    landing = make_arrow(frame=4, total_frames=5)
    flying = make_arrow(frame=0, total_frames=5)
    engine.arrows[:] = [landing, flying]

    engine.tick()

    assert engine.arrows == [flying]
    assert flying["frame"] == 1


def test_tick_grows_wheat_fields(engine: GameEngine) -> None:
    field = WheatField(0, 0)
    engine.resources.append(field)

    engine.tick()

    assert field.growth == 1


def test_tick_removes_dead_fauna(engine: GameEngine) -> None:
    dead = engine.fauna[0]
    dead.health = 0

    engine.tick()

    assert dead not in engine.fauna


@pytest.mark.parametrize(
    ("is_dead_npc_selected", "expected_selected_index"),
    [(True, 0), (False, None)],
    ids=["selected-npc-dies", "unselected-npc-dies"],
)
def test_tick_removes_dead_npcs_and_hands_the_selection_to_a_survivor(
    engine: GameEngine, is_dead_npc_selected: bool, expected_selected_index: int | None
) -> None:
    dead = engine.npcs[1]
    dead.selected = is_dead_npc_selected
    dead.health = 0

    engine.tick()

    assert dead not in engine.npcs
    selected = [index for index, npc in enumerate(engine.npcs) if npc.selected]
    assert selected == ([] if expected_selected_index is None else [expected_selected_index])
