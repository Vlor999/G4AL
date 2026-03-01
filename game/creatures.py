"""Creature hierarchy – base class for all living entities on the map.

Creature (abstract-ish base)
├── Pawn     – playable units (NPC class in npc.py, gets `kind='pawn'`)
├── Archer   – playable ranged units (Archer class in npc.py, `kind='archer'`)
└── Fauna    – autonomous non-playable creatures
    ├── Sheep      – grazes, wanders, idles on its own
    ├── Cat        – sits in one spot, animated decoration
    └── WildArcher – patrols, idles, occasionally shoots (Red team)
"""

from __future__ import annotations

import math
import random
from enum import Enum, auto
from typing import List, Tuple, Optional, TYPE_CHECKING

from game.settings import (
    TILE_SIZE,
    ARCHER_FIRE_ANIM_TIME,
    WILD_ARCHER_RANGE,
    WILD_ARCHER_DAMAGE,
    WILD_ARCHER_SHOOT_TIME,
    ARCHER_ARROW_FLIGHT,
)

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
    SHOOTING = auto()  # used by WildArcher: brief "shoot" animation pose


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
#  Cat – sits in one place, purely decorative animated fauna
# ═══════════════════════════════════════════════════════════════════════════


class Cat(Fauna):
    """A cat that sits in one spot and loops its idle animation."""

    kind = "cat"

    def __init__(
        self,
        x: float,
        y: float,
        game_map: "GameMap",
        resources: List["Resource"],
    ):
        super().__init__(x, y, game_map, resources, name="Le Chat")
        self.speed = 0.0
        self.health = 50
        self.max_health = 50
        self.state = FaunaState.IDLE
        self._idle_duration = 999_999  # never leaves idle

    def update(self):
        """Cat does nothing — purely animated on the frontend."""
        pass


# ═══════════════════════════════════════════════════════════════════════════
#  WildArcher – autonomous hostile archer (Red team)
# ═══════════════════════════════════════════════════════════════════════════

_WILD_ARCHER_NAMES = [
    "Bandit", "Outlaw", "Rogue", "Poacher", "Marauder", "Raider",
]
_used_wild_archer_names: list[str] = []


def _pick_wild_name() -> str:
    available = [n for n in _WILD_ARCHER_NAMES if n not in _used_wild_archer_names]
    if not available:
        _used_wild_archer_names.clear()
        available = list(_WILD_ARCHER_NAMES)
    name = random.choice(available)
    _used_wild_archer_names.append(name)
    return name


class WildArcher(Fauna):
    """Autonomous red archer that patrols, idles, and attacks nearby units."""

    kind = "wild_archer"

    def __init__(
        self,
        x: float,
        y: float,
        game_map: "GameMap",
        resources: List["Resource"],
    ):
        super().__init__(x, y, game_map, resources, name=_pick_wild_name())
        self.speed = 1.5
        self.health = 50
        self.max_health = 50
        self._shoot_duration = 0
        self._attack_target = None  # NPC we are shooting at
        self._all_npcs: list = []   # set by server after spawn
        self._arrows: list = []     # shared arrow projectile list
        self._is_firing: bool = False  # True during brief fire anim
        self._start_idle()

    def update(self):
        """Override base: adds SHOOTING + CHASING states."""
        if self.health <= 0:
            return
        if self.state == FaunaState.IDLE:
            self._do_idle()
        elif self.state == FaunaState.WANDERING:
            self._do_wander()
        elif self.state == FaunaState.SHOOTING:
            self._do_shoot()

    # ── enemy detection ──────────────────────────────────────────────────

    def _find_nearest_npc(self):
        """Find the nearest living playable NPC."""
        best = None
        best_dist = float("inf")
        mc, mr = self.tile_pos
        for npc in self._all_npcs:
            if npc.health <= 0:
                continue
            nc, nr = npc.tile_pos
            d = abs(nc - mc) + abs(nr - mr)
            if d < best_dist:
                best_dist = d
                best = npc
        return best, best_dist

    # ── overrides / new behaviours ───────────────────────────────────────

    def _do_idle(self):
        self._timer += 1
        if self._timer >= self._idle_duration:
            self._timer = 0
            # Check for nearby enemies first
            target, dist = self._find_nearest_npc()
            if target and dist <= WILD_ARCHER_RANGE:
                self._attack_target = target
                self._start_shoot()
                return
            if target and dist <= 6:
                # Chase toward the player unit
                self._chase_target(target)
                return
            roll = random.random()
            if roll < 0.35:
                self._start_wander()
            else:
                self._idle_duration = random.randint(90, 300)

    def _start_wander(self):
        """Patrol a wider radius than sheep."""
        col, row = self.tile_pos
        target = self._random_nearby_walkable(col, row, radius=8)
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

    def _do_wander(self):
        """Override: check for enemies while walking."""
        if self._path_index >= len(self._path):
            self._start_idle()
            return
        # Scan for nearby enemies while patrolling
        target, dist = self._find_nearest_npc()
        if target and dist <= WILD_ARCHER_RANGE:
            self._attack_target = target
            self._start_shoot()
            return
        self._follow_path()

    def _chase_target(self, target):
        """Walk toward a player unit to get in attack range."""
        tc, tr = target.tile_pos
        mc, mr = self.tile_pos
        # Find closest walkable tile within range of target
        best_tile = None
        best_cost = float("inf")
        for dc in range(-WILD_ARCHER_RANGE, WILD_ARCHER_RANGE + 1):
            for dr in range(-WILD_ARCHER_RANGE, WILD_ARCHER_RANGE + 1):
                if abs(dc) + abs(dr) > WILD_ARCHER_RANGE:
                    continue
                c, r = tc + dc, tr + dr
                if not self._map.is_walkable(c, r):
                    continue
                cost = abs(c - mc) + abs(r - mr)
                if cost < best_cost:
                    best_cost = cost
                    best_tile = (c, r)
        if best_tile is None:
            self._start_idle()
            return
        path = self._simple_path((mc, mr), best_tile)
        if not path:
            self._start_idle()
            return
        self._path = path
        self._path_index = 0
        self.state = FaunaState.WANDERING

    def _start_shoot(self):
        """Begin shooting at the current attack target."""
        self.state = FaunaState.SHOOTING
        self._timer = 0
        self._shoot_duration = WILD_ARCHER_SHOOT_TIME
        self._is_firing = False

    def _do_shoot(self):
        self._timer += 1
        target = self._attack_target
        # Target dead or gone
        if target is None or target.health <= 0:
            self._attack_target = None
            self._is_firing = False
            self._start_idle()
            return

        fire_start = self._shoot_duration - ARCHER_FIRE_ANIM_TIME

        # Transition aim → fire phase
        if not self._is_firing and self._timer >= fire_start:
            self._is_firing = True
            # Check range before firing
            mc, mr = self.tile_pos
            tc, tr = target.tile_pos
            dist = abs(tc - mc) + abs(tr - mr)
            if dist > WILD_ARCHER_RANGE:
                self._attack_target = None
                self._is_firing = False
                self._start_idle()
                return
            # Deal damage + spawn arrow
            target.health = max(0, target.health - WILD_ARCHER_DAMAGE)
            if self._arrows is not None:
                self._arrows.append({
                    "fromX": self.x,
                    "fromY": self.y - 20,
                    "toX": target.x,
                    "toY": target.y - 10,
                    "frame": 0,
                    "totalFrames": ARCHER_ARROW_FLIGHT,
                    "team": "red",
                })

        # End of full cycle
        if self._timer >= self._shoot_duration:
            self._is_firing = False
            if target.health > 0:
                self._timer = 0  # reset for next shot
            else:
                self._attack_target = None
                self._start_idle()


# ═══════════════════════════════════════════════════════════════════════════
#  Spawning helper
# ═══════════════════════════════════════════════════════════════════════════


def spawn_fauna(
    game_map: "GameMap",
    resources: List["Resource"],
    sheep_count: int = 5,
    wild_archer_count: int = 3,
) -> List[Fauna]:
    """Place sheep, wild archers on walkable tiles + one cat in a corner."""
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

    def _random_edge():
        """Pick a walkable tile near the map edges (patrol spawn)."""
        for _ in range(300):
            side = random.randint(0, 3)
            if side == 0:  # top
                c = random.randint(1, game_map.cols - 2)
                r = random.randint(1, 3)
            elif side == 1:  # bottom
                c = random.randint(1, game_map.cols - 2)
                r = random.randint(game_map.rows - 4, game_map.rows - 2)
            elif side == 2:  # left
                c = random.randint(1, 3)
                r = random.randint(1, game_map.rows - 2)
            else:  # right
                c = random.randint(game_map.cols - 4, game_map.cols - 2)
                r = random.randint(1, game_map.rows - 2)
            if game_map.is_walkable(c, r) and (c, r) not in occupied:
                return c, r
        return None

    for _ in range(sheep_count):
        pos = _random_grass()
        if pos:
            occupied.add(pos)
            wx, wy = game_map.tile_center(*pos)
            fauna.append(Sheep(wx, wy, game_map, resources))

    # Wild archers on map edges
    for _ in range(wild_archer_count):
        pos = _random_edge()
        if pos:
            occupied.add(pos)
            wx, wy = game_map.tile_center(*pos)
            fauna.append(WildArcher(wx, wy, game_map, resources))

    # Place one cat in a corner of the map
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
            fauna.append(Cat(wx, wy, game_map, resources))
            break

    return fauna
