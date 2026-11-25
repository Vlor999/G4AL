"""Drive GameEngine's tick and game loop with fake ports and a fake socket emitter."""

from collections.abc import Iterator
from typing import Any, cast

import pytest
from flask_socketio import SocketIO
from loguru import logger

from game.combat.arrows import Arrow
from game.fauna.wild_archer import WildArcher
from game.npcs.actions import Action, ActionType
from game.npcs.archer import Archer
from game.resources.entities import WheatField
from server.engine import GameEngine

MAX_FRAMES = 600


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


def test_tick_grows_wheat_fields(engine: GameEngine) -> None:
    field = WheatField(0, 0)
    engine.resources.append(field)

    engine.tick()

    assert field.growth == 1


def test_an_archer_shoots_a_creature_added_after_tick_removed_the_dead(
    engine: GameEngine,
) -> None:
    spawn_point = engine.npcs[0]
    archer = Archer(spawn_point.x, spawn_point.y, engine.game_map, [], engine.storage)
    archer.link_battlefield(fauna=engine.fauna, arrows=engine.arrows)
    engine.npcs[:] = [archer]
    for creature in engine.fauna:
        creature.health = 0

    engine.tick()
    newcomer = WildArcher(archer.x, archer.y, engine.game_map, engine.resources)
    engine.fauna.append(newcomer)
    archer.enqueue(Action(ActionType.SHOOT))
    for _ in range(MAX_FRAMES):
        if newcomer.health < newcomer.max_health:
            break
        engine.tick()

    assert newcomer.health < newcomer.max_health
