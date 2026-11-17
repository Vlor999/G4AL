"""A* pathfinding on the tile grid."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.map import GameMap


def _heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(
    game_map: GameMap,
    start: tuple[int, int],
    goal: tuple[int, int],
    blocked: set[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """A* on the tile grid. Returns list of (col, row) from start to goal (inclusive).

    *blocked* is an optional set of (col, row) tiles treated as impassable
    (e.g. tiles occupied by other NPCs).  The *goal* tile itself is never
    considered blocked so that NPCs can still path toward a destination
    even if one of them is standing on it.
    """
    import heapq

    if not game_map.is_walkable(goal[0], goal[1]):
        for dc, dr in [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1),
        ]:
            nc, nr = goal[0] + dc, goal[1] + dr
            if game_map.is_walkable(nc, nr):
                goal = (nc, nr)
                break
        else:
            return []

    open_set: list[tuple[float, tuple[int, int]]] = []
    heapq.heappush(open_set, (0.0, start))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (current[0] + dc, current[1] + dr)
            if not game_map.is_walkable(neighbor[0], neighbor[1]):
                continue
            if blocked and neighbor in blocked and neighbor != goal:
                continue
            tentative = g_score[current] + 1
            if tentative < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f = tentative + _heuristic(neighbor, goal)
                heapq.heappush(open_set, (f, neighbor))
    return []
