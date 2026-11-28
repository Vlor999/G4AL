"""Where the land meets a lake: the shore tile an NPC goes to for a water action."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

from game.world.pathfinding import ORTHOGONAL_STEPS, Tile

if TYPE_CHECKING:
    from game.world.map import GameMap


@dataclass(frozen=True)
class ShoreSpot:
    """A walkable ``shore_tile`` and the ``water_tile`` that shares an edge with it."""

    shore_tile: Tile
    water_tile: Tile


def find_shore_spot(game_map: GameMap, start: Tile, *, blocked: set[Tile]) -> ShoreSpot | None:
    """The shore spot nearest to *start* by walking distance; None when no walkable tile
    next to water can be reached.

    The walk follows ``find_path``'s rules: orthogonal steps on walkable tiles, never
    onto *blocked* ones (the tiles resources cover), so a path to the shore tile exists.
    """
    visited = {start}
    queue = deque([start])
    while queue:
        tile = queue.popleft()
        water_tile = _find_water_neighbor(game_map, tile)
        if water_tile is not None:
            return ShoreSpot(shore_tile=tile, water_tile=water_tile)
        for dc, dr in ORTHOGONAL_STEPS:
            neighbor = (tile[0] + dc, tile[1] + dr)
            if neighbor in visited or neighbor in blocked or not game_map.is_walkable(*neighbor):
                continue
            visited.add(neighbor)
            queue.append(neighbor)
    return None


def _find_water_neighbor(game_map: GameMap, tile: Tile) -> Tile | None:
    for dc, dr in ORTHOGONAL_STEPS:
        neighbor = (tile[0] + dc, tile[1] + dr)
        if game_map.is_water(*neighbor):
            return neighbor
    return None
