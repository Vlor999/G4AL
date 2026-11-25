"""Placement of the fauna on a new map: sheep, wild archers and the cat."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.fauna.cat import Cat
from game.fauna.sheep import Sheep
from game.fauna.wild_archer import WildArcher
from game.settings import SHEEP_BIOMES
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


def _find_random_edge_tile(
    game_map: GameMap, occupied: set[tuple[int, int]]
) -> tuple[int, int] | None:
    """Pick a walkable tile near the map edges (patrol spawn)."""
    for _ in range(300):
        side = game_map.rng.randint(0, 3)
        if side == 0:
            c = game_map.rng.randint(1, game_map.cols - 2)
            r = game_map.rng.randint(1, 3)
        elif side == 1:
            c = game_map.rng.randint(1, game_map.cols - 2)
            r = game_map.rng.randint(game_map.rows - 4, game_map.rows - 2)
        elif side == 2:
            c = game_map.rng.randint(1, 3)
            r = game_map.rng.randint(1, game_map.rows - 2)
        else:
            c = game_map.rng.randint(game_map.cols - 4, game_map.cols - 2)
            r = game_map.rng.randint(1, game_map.rows - 2)
        if game_map.is_walkable(c, r) and (c, r) not in occupied:
            return c, r
    return None


def _place_cat_in_corner(
    game_map: GameMap,
    resources: list[Resource],
    *,
    occupied: set[tuple[int, int]],
) -> Cat | None:
    corners = [
        (2, 2),
        (game_map.cols - 3, 2),
        (2, game_map.rows - 3),
        (game_map.cols - 3, game_map.rows - 3),
    ]
    for col, row in corners:
        if game_map.is_walkable(col, row) and (col, row) not in occupied:
            occupied.add((col, row))
            wx, wy = game_map.tile_center(col, row)
            return Cat(wx, wy, game_map, resources)
    return None


def spawn_fauna(
    game_map: GameMap,
    resources: list[Resource],
    sheep_count: int = 5,
    wild_archer_count: int = 3,
) -> list[Fauna]:
    """Sheep on free grass tiles, meadow first, wild archers near the map edges and one cat in a corner."""
    fauna: list[Fauna] = []
    occupied: set[tuple[int, int]] = {(r.col, r.row) for r in resources}

    for _ in range(sheep_count):
        pos = _find_sheep_tile(game_map, occupied)
        if pos:
            occupied.add(pos)
            wx, wy = game_map.tile_center(*pos)
            fauna.append(Sheep(wx, wy, game_map, resources))

    for _ in range(wild_archer_count):
        pos = _find_random_edge_tile(game_map, occupied)
        if pos:
            occupied.add(pos)
            wx, wy = game_map.tile_center(*pos)
            fauna.append(WildArcher(wx, wy, game_map, resources))

    cat = _place_cat_in_corner(game_map, resources, occupied=occupied)
    if cat is not None:
        fauna.append(cat)

    return fauna
