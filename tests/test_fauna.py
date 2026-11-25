"""Autonomous fauna on hand-built worlds: wander, graze, removal of the dead."""

import pytest

from game.fauna.fauna import Fauna, FaunaState, remove_dead_fauna
from game.fauna.sheep import Sheep
from game.fauna.wild_archer import WildArcher
from game.world.map import GameMap
from tests.conftest import MapBuilder

MEADOW = ["." * 30] * 30
FRAMES = 6000


def wander_legs(creature: Fauna, frames: int) -> list[int]:
    """Tile distance (Chebyshev) covered by each finished wander, frame by frame."""
    legs: list[int] = []
    start = creature.tile_pos
    previous_state = creature.state
    for _ in range(frames):
        creature.update()
        if creature.state == FaunaState.WANDERING and previous_state != FaunaState.WANDERING:
            start = creature.tile_pos
        if previous_state == FaunaState.WANDERING and creature.state != FaunaState.WANDERING:
            (start_col, start_row), (col, row) = start, creature.tile_pos
            legs.append(max(abs(col - start_col), abs(row - start_row)))
        previous_state = creature.state
    return legs


def place(kind: type[Sheep] | type[WildArcher], game_map: GameMap) -> Fauna:
    return kind(*game_map.tile_center(15, 15), game_map, [])


@pytest.mark.parametrize(
    ("kind", "wander_radius", "seeded_legs"),
    [(Sheep, 5, [4, 1, 5, 5]), (WildArcher, 8, [8, 6, 2, 6, 1, 7, 4, 1])],
    ids=["sheep", "wild-archer"],
)
def test_fauna_wanders_within_its_radius(
    build_map: MapBuilder,
    kind: type[Sheep] | type[WildArcher],
    wander_radius: int,
    seeded_legs: list[int],
) -> None:
    creature = place(kind, build_map(MEADOW))

    legs = wander_legs(creature, FRAMES)

    assert max(legs) <= wander_radius
    assert legs == seeded_legs


def test_a_sheep_alternates_idling_grazing_and_wandering(build_map: MapBuilder) -> None:
    sheep = place(Sheep, build_map(MEADOW))
    states: set[FaunaState] = set()

    for _ in range(FRAMES):
        sheep.update()
        states.add(sheep.state)

    assert states == {FaunaState.IDLE, FaunaState.GRAZING, FaunaState.WANDERING}


def test_a_sheep_on_an_island_stays_on_its_tile(build_map: MapBuilder) -> None:
    game_map = build_map(["~~~", "~.~", "~~~"])
    sheep = Sheep(*game_map.tile_center(1, 1), game_map, [])

    for _ in range(FRAMES):
        sheep.update()

    assert sheep.tile_pos == (1, 1)


def test_remove_dead_fauna_drops_the_dead_creatures(build_map: MapBuilder) -> None:
    game_map = build_map(["." * 4])
    alive, dead = (Sheep(*game_map.tile_center(col, 0), game_map, []) for col in (0, 1))
    dead.health = 0
    fauna = [alive, dead]

    remove_dead_fauna(fauna)

    assert fauna == [alive]
