"""Tile-distance searches of combat: the nearest living target, a tile to shoot from."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol, TypeVar

if TYPE_CHECKING:
    from game.world.map import GameMap


class Combatant(Protocol):
    @property
    def tile_pos(self) -> tuple[int, int]: ...

    @property
    def health(self) -> float: ...


CombatantT = TypeVar("CombatantT", bound=Combatant)


def tile_distance(first: tuple[int, int], second: tuple[int, int]) -> int:
    """Manhattan distance between two tiles."""
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def find_nearest_living(
    origin: tuple[int, int],
    candidates: Iterable[CombatantT],
    *,
    max_distance: int | None = None,
) -> CombatantT | None:
    """The living candidate nearest to *origin*, the earliest one on a tie.

    None when no living candidate lies within *max_distance* tiles (no bound when None).
    """
    nearest: CombatantT | None = None
    nearest_distance = float("inf")
    for candidate in candidates:
        if candidate.health <= 0:
            continue
        distance = tile_distance(origin, candidate.tile_pos)
        if max_distance is not None and distance > max_distance:
            continue
        if distance < nearest_distance:
            nearest_distance = distance
            nearest = candidate
    return nearest


def find_walkable_tile_in_range(
    game_map: GameMap,
    *,
    origin: tuple[int, int],
    target: tuple[int, int],
    shooting_range: int,
) -> tuple[int, int] | None:
    """The walkable tile within *shooting_range* of *target* nearest to *origin*.

    None when no tile in range is walkable; reachability is not checked.
    """
    target_col, target_row = target
    best_tile: tuple[int, int] | None = None
    best_cost = float("inf")
    for dc in range(-shooting_range, shooting_range + 1):
        for dr in range(-shooting_range, shooting_range + 1):
            if abs(dc) + abs(dr) > shooting_range:
                continue
            tile = (target_col + dc, target_row + dr)
            if not game_map.is_walkable(*tile):
                continue
            cost = tile_distance(tile, origin)
            if cost < best_cost:
                best_cost = cost
                best_tile = tile
    return best_tile
