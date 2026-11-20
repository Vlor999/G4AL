"""Fauna: the autonomous, non-playable creatures of the map and their idle, graze and
wander cycle."""

from __future__ import annotations

import heapq
import math
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.entities import Resource
    from game.map import GameMap


class FaunaState(Enum):
    IDLE = auto()
    WANDERING = auto()
    GRAZING = auto()
    SHOOTING = auto()


# Fauna ids start high so they never collide with NPC ids in the client state.
_fauna_next_id = 10_000


def _next_fauna_id() -> int:
    global _fauna_next_id
    _fauna_next_id += 1
    return _fauna_next_id


class Fauna:
    """A creature that idles, grazes and wanders on its own; subclasses set its stats."""

    kind: str = "fauna"
    controllable: bool = False
    wander_radius: int = 5

    def __init__(
        self,
        x: float,
        y: float,
        game_map: GameMap,
        resources: list[Resource],
        name: str = "Fauna",
    ):
        self.id = _next_fauna_id()
        self.name = name
        self.x = x
        self.y = y
        self.health = 30
        self.max_health = 30
        self.speed = 1.0

        self._map = game_map
        self._resources = resources

        self.state = FaunaState.IDLE
        self._path: list[tuple[int, int]] = []
        self._path_index = 0
        self._timer = 0  # frames spent in the current state
        self._idle_duration = 0
        self._graze_duration = 0

    @property
    def tile_pos(self) -> tuple[int, int]:
        return self._map.world_to_tile(self.x, self.y)

    @property
    def is_firing(self) -> bool:
        """True while the shot animation is active; this default means the kind never shoots."""
        return False

    def update(self) -> None:
        """Advance the behaviour by one frame."""
        if self.state == FaunaState.IDLE:
            self._do_idle()
        elif self.state == FaunaState.WANDERING:
            self._do_wander()
        elif self.state == FaunaState.GRAZING:
            self._do_graze()

    def _do_idle(self) -> None:
        self._timer += 1
        if self._timer >= self._idle_duration:
            self._timer = 0
            if self._map.rng.random() < 0.5:
                self._start_graze()
            else:
                self._start_wander()

    def _do_wander(self) -> None:
        if self._path_index >= len(self._path):
            self._start_idle()
            return
        self._follow_path()

    def _do_graze(self) -> None:
        self._timer += 1
        if self._timer >= self._graze_duration:
            self._start_idle()

    def _start_idle(self) -> None:
        self.state = FaunaState.IDLE
        self._timer = 0
        self._idle_duration = self._map.rng.randint(60, 240)

    def _start_wander(self) -> None:
        col, row = self.tile_pos
        target = self._random_nearby_walkable(col, row, radius=self.wander_radius)
        if target is None:
            self._start_idle()
            return
        self._walk_to(target)

    def _walk_to(self, goal: tuple[int, int]) -> None:
        """Path to *goal* in WANDERING, or go idle when no path reaches it."""
        path = self._simple_path(self.tile_pos, goal)
        if not path:
            self._start_idle()
            return
        self._path = path
        self._path_index = 0
        self.state = FaunaState.WANDERING

    def _start_graze(self) -> None:
        self.state = FaunaState.GRAZING
        self._timer = 0
        self._graze_duration = self._map.rng.randint(120, 360)

    def _follow_path(self) -> None:
        if self._path_index >= len(self._path):
            return
        target_col, target_row = self._path[self._path_index]
        tx, ty = self._map.tile_center(target_col, target_row)
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < self.speed:
            self.x, self.y = tx, ty
            self._path_index += 1
        else:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def _random_nearby_walkable(
        self, col: int, row: int, radius: int = 5
    ) -> tuple[int, int] | None:
        candidates = []
        for dc in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                nc, nr = col + dc, row + dr
                if self._map.is_walkable(nc, nr):
                    candidates.append((nc, nr))
        if not candidates:
            return None
        return self._map.rng.choice(candidates)

    def _simple_path(self, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
        """A* over walkable tiles, ignoring structures and other creatures; [] when unreachable."""
        if not self._map.is_walkable(goal[0], goal[1]):
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
                if not self._map.is_walkable(neighbor[0], neighbor[1]):
                    continue
                tentative = g_score[current] + 1
                if tentative < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    h = abs(neighbor[0] - goal[0]) + abs(neighbor[1] - goal[1])
                    heapq.heappush(open_set, (tentative + h, neighbor))
        return []


def remove_dead_fauna(fauna: list[Fauna]) -> None:
    """Drop the dead creatures from *fauna* in place: archers hold this same list."""
    fauna[:] = [creature for creature in fauna if creature.health > 0]
