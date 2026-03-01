"""Creature hierarchy – base class for all living entities on the map.

Creature (abstract-ish base)
├── Pawn     – playable units (NPC class in npc.py, gets `kind='pawn'`)
└── Fauna    – autonomous non-playable creatures
    └── Sheep – grazes, wanders, idles on its own
"""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import List, Tuple, Optional, TYPE_CHECKING

from game.settings import TILE_SIZE

if TYPE_CHECKING:
    from game.map import GameMap
    from game.entities import Resource


# ═══════════════════════════════════════════════════════════════════════════
#  Fauna states
# ═══════════════════════════════════════════════════════════════════════════


class FaunaState(Enum):
    IDLE = auto()
    WANDERING = auto()
    GRAZING = auto()


# ═══════════════════════════════════════════════════════════════════════════
#  Fauna – autonomous non-playable creature base
# ═══════════════════════════════════════════════════════════════════════════

_fauna_next_id = 10_000  # start high to avoid collisions with NPC ids


def _next_fauna_id() -> int:
    global _fauna_next_id
    _fauna_next_id += 1
    return _fauna_next_id


class Fauna:
    """Non-playable autonomous creature that lives on the map."""

    kind: str = "fauna"
    controllable: bool = False

    def __init__(
        self,
        x: float,
        y: float,
        game_map: "GameMap",
        resources: List["Resource"],
        name: str = "Fauna",
    ):
        self.id = _next_fauna_id()
        self.name = name
        self.x = x
        self.y = y
        self.health = 30
        self.max_health = 30
        self.speed = 1.0

        # refs
        self._map = game_map
        self._resources = resources

        # state
        self.state = FaunaState.IDLE
        self._path: List[Tuple[int, int]] = []
        self._path_index = 0
        self._timer = 0  # generic tick counter
        self._idle_duration = 0
        self._graze_duration = 0

    @property
    def tile_pos(self) -> Tuple[int, int]:
        return self._map.world_to_tile(self.x, self.y)

    def update(self):
        """Called every frame. Drives the autonomous behaviour loop."""
        if self.state == FaunaState.IDLE:
            self._do_idle()
        elif self.state == FaunaState.WANDERING:
            self._do_wander()
        elif self.state == FaunaState.GRAZING:
            self._do_graze()

    # ── behaviour phases ─────────────────────────────────────────────────

    def _do_idle(self):
        self._timer += 1
        if self._timer >= self._idle_duration:
            self._timer = 0
            # decide what to do next
            if random.random() < 0.5:
                self._start_graze()
            else:
                self._start_wander()

    def _do_wander(self):
        if self._path_index >= len(self._path):
            # arrived – go idle for a bit
            self._start_idle()
            return
        self._follow_path()

    def _do_graze(self):
        self._timer += 1
        if self._timer >= self._graze_duration:
            self._start_idle()

    # ── transitions ──────────────────────────────────────────────────────

    def _start_idle(self):
        self.state = FaunaState.IDLE
        self._timer = 0
        self._idle_duration = random.randint(60, 240)  # 1-4 seconds at 60fps

    def _start_wander(self):
        """Pick a random nearby walkable tile and path to it."""
        col, row = self.tile_pos
        target = self._random_nearby_walkable(col, row, radius=5)
        if target is None:
            self._start_idle()
            return
        path = self._simple_path((col, row), target)
        if not path:
            self._start_idle()
            return
        self._path = path
        self._path_index = 0
        self.state = FaunaState.WANDERING

    def _start_graze(self):
        self.state = FaunaState.GRAZING
        self._timer = 0
        self._graze_duration = random.randint(120, 360)  # 2-6 seconds

    # ── movement ─────────────────────────────────────────────────────────

    def _follow_path(self):
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

    # ── helpers ──────────────────────────────────────────────────────────

    def _random_nearby_walkable(
        self, col: int, row: int, radius: int = 5
    ) -> Optional[Tuple[int, int]]:
        """Pick a random walkable tile within *radius* of (col, row)."""
        candidates = []
        for dc in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                nc, nr = col + dc, row + dr
                if self._map.is_walkable(nc, nr):
                    candidates.append((nc, nr))
        if not candidates:
            return None
        return random.choice(candidates)

    def _simple_path(
        self, start: Tuple[int, int], goal: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """Lightweight A* for fauna (no NPC collision avoidance)."""
        import heapq

        if not self._map.is_walkable(goal[0], goal[1]):
            return []

        open_set: list = []
        heapq.heappush(open_set, (0.0, start))
        came_from: dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: dict[Tuple[int, int], float] = {start: 0.0}

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


# ═══════════════════════════════════════════════════════════════════════════
#  Sheep
# ═══════════════════════════════════════════════════════════════════════════


class Sheep(Fauna):
    """Autonomous sheep that wanders and grazes on grass tiles."""

    kind = "sheep"

    def __init__(
        self,
        x: float,
        y: float,
        game_map: "GameMap",
        resources: List["Resource"],
    ):
        super().__init__(x, y, game_map, resources, name="Sheep")
        self.speed = 0.8  # slower than pawns
        self.health = 20
        self.max_health = 20
        self._start_idle()  # kick-start behaviour


# ═══════════════════════════════════════════════════════════════════════════
#  Spawning helper
# ═══════════════════════════════════════════════════════════════════════════


def spawn_fauna(
    game_map: "GameMap",
    resources: List["Resource"],
    sheep_count: int = 5,
) -> List[Fauna]:
    """Place sheep randomly on walkable grass tiles."""
    from game.map import TileType

    fauna: List[Fauna] = []
    occupied: set[Tuple[int, int]] = {(r.col, r.row) for r in resources}

    def _random_grass():
        for _ in range(200):
            c = random.randint(1, game_map.cols - 2)
            r = random.randint(1, game_map.rows - 2)
            if (
                game_map.is_walkable(c, r)
                and game_map.tiles[r][c] == TileType.GRASS
                and (c, r) not in occupied
            ):
                return c, r
        return None

    for _ in range(sheep_count):
        pos = _random_grass()
        if pos:
            occupied.add(pos)
            wx, wy = game_map.tile_center(*pos)
            fauna.append(Sheep(wx, wy, game_map, resources))

    return fauna
