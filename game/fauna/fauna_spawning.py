"""Placement of the fauna on a new map: sheep and the cat."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.fauna.cat import Cat
from game.fauna.sheep import Sheep
from game.settings import CAT_CORNER_MARGIN, SHEEP_BIOMES
from game.world.terrain import TileType

if TYPE_CHECKING:
    from game.fauna.fauna import Fauna
    from game.resources.entities import Resource
    from game.world.map import GameMap


def _find_sheep_tile(game_map: GameMap, occupied: set[tuple[int, int]]) -> tuple[int, int] | None:
    """A free grass tile inside the map border, in a sheep biome when one is left."""
    grass = [
        (col, row)
        for row in range(1, game_map.rows - 1)
        for col in range(1, game_map.cols - 1)
        if game_map.tiles[row][col] == TileType.GRASS and (col, row) not in occupied
    ]
    pasture = [(col, row) for col, row in grass if game_map.biomes[row][col] in SHEEP_BIOMES]
    candidates = pasture or grass
    return game_map.rng.choice(candidates) if candidates else None


def _place_cat_in_corner(
    game_map: GameMap,
    *,
    occupied: set[tuple[int, int]],
) -> Cat | None:
    near = CAT_CORNER_MARGIN
    far_col = game_map.cols - 1 - CAT_CORNER_MARGIN
    far_row = game_map.rows - 1 - CAT_CORNER_MARGIN
    corners = [(near, near), (far_col, near), (near, far_row), (far_col, far_row)]
    for col, row in corners:
        if game_map.is_walkable(col, row) and (col, row) not in occupied:
            occupied.add((col, row))
            wx, wy = game_map.tile_center(col, row)
            return Cat(wx, wy, game_map)
    return None


def spawn_fauna(
    game_map: GameMap,
    resources: list[Resource],
    sheep_count: int = 5,
) -> list[Fauna]:
    """Sheep on free grass tiles, meadow first, and one cat in a corner."""
    fauna: list[Fauna] = []
    occupied: set[tuple[int, int]] = {(r.col, r.row) for r in resources}

    for _ in range(sheep_count):
        pos = _find_sheep_tile(game_map, occupied)
        if pos:
            occupied.add(pos)
            wx, wy = game_map.tile_center(*pos)
            fauna.append(Sheep(wx, wy, game_map))

    cat = _place_cat_in_corner(game_map, occupied=occupied)
    if cat is not None:
        fauna.append(cat)

    return fauna
