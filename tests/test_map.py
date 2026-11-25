import pytest

from game.settings import TILE_SIZE
from game.world.map import GameMap
from tests.conftest import MapBuilder

GRID = [
    ".:s~~",
    ".....",
    ".....",
    ".....",
    ".....",
    ".....",
    ".....",
]


@pytest.mark.parametrize(
    ("col", "row", "expected"),
    [
        (0, 0, True),
        (1, 0, True),
        (2, 0, True),
        (3, 0, False),
        (-1, 0, False),
        (5, 0, False),
        (0, 7, False),
    ],
)
def test_is_walkable(build_map: MapBuilder, col: int, row: int, expected: bool) -> None:
    assert build_map(GRID).is_walkable(col, row) is expected


@pytest.mark.parametrize(("col", "row"), [(0, 0), (3, 2), (4, 6)])
def test_world_to_tile_inverts_tile_center(build_map: MapBuilder, col: int, row: int) -> None:
    game_map = build_map(GRID)
    x, y = game_map.tile_center(col, row)
    assert game_map.world_to_tile(x, y) == (col, row)


def test_tile_center_is_middle_of_tile(build_map: MapBuilder) -> None:
    assert build_map(GRID).tile_center(1, 2) == (1.5 * TILE_SIZE, 2.5 * TILE_SIZE)


def test_generation_is_reproducible_with_a_seed() -> None:
    first = GameMap(cols=12, rows=9, seed=7)
    second = GameMap(cols=12, rows=9, seed=7)
    assert first.tiles == second.tiles
    assert len(first.tiles) == 9
    assert all(len(row) == 12 for row in first.tiles)
