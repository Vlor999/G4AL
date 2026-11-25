"""A* pathfinding and nearest-tile search on the tile grid."""

from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.map import GameMap

Tile = tuple[int, int]

_ORTHOGONAL_STEPS: tuple[Tile, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
_GOAL_FALLBACK_STEPS: tuple[Tile, ...] = (*_ORTHOGONAL_STEPS, (-1, -1), (1, -1), (-1, 1), (1, 1))


def _heuristic(a: Tile, b: Tile) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(
    game_map: GameMap,
    start: Tile,
    goal: Tile,
    blocked: set[Tile] | None = None,
) -> list[Tile]:
    """A* on the tile grid: the (col, row) tiles from *start* to *goal*, both included, or
    [] when no path exists.

    An unwalkable *goal* is replaced by its first walkable neighbour. *blocked* tiles (other
    NPCs) are impassable, except the goal itself, so an NPC can still head for a tile
    another one stands on.
    """
    reachable_goal = _nearest_walkable_goal(game_map, goal)
    if reachable_goal is None:
        return []
    return _search_path(game_map, start, goal=reachable_goal, blocked=blocked or set())


def _nearest_walkable_goal(game_map: GameMap, goal: Tile) -> Tile | None:
    if game_map.is_walkable(*goal):
        return goal
    for dc, dr in _GOAL_FALLBACK_STEPS:
        neighbor = (goal[0] + dc, goal[1] + dr)
        if game_map.is_walkable(*neighbor):
            return neighbor
    return None


def _search_path(game_map: GameMap, start: Tile, *, goal: Tile, blocked: set[Tile]) -> list[Tile]:
    open_set: list[tuple[float, Tile]] = [(0.0, start)]
    came_from: dict[Tile, Tile] = {}
    g_score: dict[Tile, float] = {start: 0.0}
    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            return _rebuild_path(came_from, current)
        for neighbor in _passable_neighbors(game_map, current, goal=goal, blocked=blocked):
            tentative = g_score[current] + 1
            if tentative < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                heapq.heappush(open_set, (tentative + _heuristic(neighbor, goal), neighbor))
    return []


def _passable_neighbors(
    game_map: GameMap, tile: Tile, *, goal: Tile, blocked: set[Tile]
) -> list[Tile]:
    neighbors = [(tile[0] + dc, tile[1] + dr) for dc, dr in _ORTHOGONAL_STEPS]
    return [
        neighbor
        for neighbor in neighbors
        if game_map.is_walkable(*neighbor) and (neighbor == goal or neighbor not in blocked)
    ]


def _rebuild_path(came_from: dict[Tile, Tile], end: Tile) -> list[Tile]:
    path = [end]
    while path[-1] in came_from:
        path.append(came_from[path[-1]])
    path.reverse()
    return path


def find_nearest_tile(
    origin: Tile, *, max_radius: int, is_suitable: Callable[[Tile], bool]
) -> Tile | None:
    """Breadth-first search outward from *origin*, through every tile and not only the
    walkable ones, for the nearest tile where *is_suitable* holds; None when no tile within
    *max_radius* columns and rows of *origin* qualifies."""
    if is_suitable(origin):
        return origin
    visited = {origin}
    queue = deque([origin])
    while queue:
        col, row = queue.popleft()
        for dc, dr in _ORTHOGONAL_STEPS:
            neighbor = (col + dc, row + dr)
            if neighbor in visited or not _is_within_radius(
                neighbor, origin=origin, radius=max_radius
            ):
                continue
            visited.add(neighbor)
            if is_suitable(neighbor):
                return neighbor
            queue.append(neighbor)
    return None


def _is_within_radius(tile: Tile, *, origin: Tile, radius: int) -> bool:
    return abs(tile[0] - origin[0]) <= radius and abs(tile[1] - origin[1]) <= radius
