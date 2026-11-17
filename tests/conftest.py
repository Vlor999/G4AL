from collections.abc import Callable

import pytest

from game.map import GameMap, TileType

_TILE_BY_SYMBOL = {
    ".": TileType.GRASS,
    ":": TileType.DIRT,
    "s": TileType.SAND,
    "~": TileType.WATER,
}

MapBuilder = Callable[[list[str]], GameMap]


@pytest.fixture
def build_map() -> MapBuilder:
    """Build a GameMap whose tiles are drawn row by row with `_TILE_BY_SYMBOL`."""

    def build(rows: list[str]) -> GameMap:
        game_map = GameMap(seed=0)
        game_map.cols = len(rows[0])
        game_map.rows = len(rows)
        game_map.tiles = [[_TILE_BY_SYMBOL[symbol] for symbol in row] for row in rows]
        return game_map

    return build
