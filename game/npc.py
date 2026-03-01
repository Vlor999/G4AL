"""NPC (bot) with Finite-State-Machine, action queue, pathfinding & stats."""

from __future__ import annotations

import math
import random
from collections import deque
from enum import Enum, auto
from typing import List, Tuple, Optional

from game.settings import (
    NPC_HUNGER_MAX,
    NPC_HUNGER_DRAIN,
    NPC_HUNGER_DAMAGE,
    NPC_EAT_TIME,
    NPC_EAT_RESTORE,
    EAT_WHEAT_COST,
    NPC_SPEED,
    NPC_MAX_HEALTH,
    NPC_CHOP_TIME,
    NPC_MINE_TIME,
    NPC_BUILD_TIME,
    BUILD_COST_WOOD,
    BUILD_COST_STONE,
    WHEAT_PLANT_TIME,
    NPC_COLLECT_UNIT_TIME,
)
from game.entities import Resource, Tree, Rock, Structure, WheatField
from api.roster import NPC_NAMES


# ═══════════════════════════════════════════════════════════════════════════
#  FSM States
# ═══════════════════════════════════════════════════════════════════════════


class State(Enum):
    IDLE = auto()
    MOVING = auto()
    PERFORMING = auto()
    RETURNING = auto()   # carrying a resource back to the storage hut
    DONE = auto()


# ═══════════════════════════════════════════════════════════════════════════
#  Action descriptors (what goes in the queue)
# ═══════════════════════════════════════════════════════════════════════════


class ActionType(Enum):
    CHOP_WOOD = "chop_wood"
    MINE_ROCK = "mine_rock"
    BUILD = "build"
    MOVE_TO = "move_to"
    EAT = "eat"
    PLANT_WHEAT = "plant_wheat"
    collect_wheat = "collect_wheat"


class Action:
    """One unit of work for an NPC."""

    def __init__(
        self,
        action_type: ActionType,
        target: Optional[Resource | Tuple[int, int]] = None,
    ):
        self.action_type = action_type
        self.target = target  # Resource instance or (col, row) for MOVE_TO


# ═══════════════════════════════════════════════════════════════════════════
#  Simple A* pathfinding on the tile grid
# ═══════════════════════════════════════════════════════════════════════════


def _heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(
    game_map: "GameMap", start: Tuple[int, int], goal: Tuple[int, int],
    blocked: set[Tuple[int, int]] | None = None,
) -> List[Tuple[int, int]]:
    """A* on the tile grid. Returns list of (col, row) from start to goal (inclusive).

    *blocked* is an optional set of (col, row) tiles treated as impassable
    (e.g. tiles occupied by other NPCs).  The *goal* tile itself is never
    considered blocked so that NPCs can still path toward a destination
    even if one of them is standing on it.
    """
    import heapq

    if not game_map.is_walkable(goal[0], goal[1]):
        # try to get an adjacent walkable tile to the goal
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

    open_set: list = []
    heapq.heappush(open_set, (0.0, start))
    came_from: dict[Tuple[int, int], Tuple[int, int]] = {}
    g_score: dict[Tuple[int, int], float] = {start: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            # reconstruct
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
            # skip tiles occupied by other NPCs (but allow the goal)
            if blocked and neighbor in blocked and neighbor != goal:
                continue
            tentative = g_score[current] + 1
            if tentative < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f = tentative + _heuristic(neighbor, goal)
                heapq.heappush(open_set, (f, neighbor))
    return []


# ═══════════════════════════════════════════════════════════════════════════
#  NPC
# ═══════════════════════════════════════════════════════════════════════════

# ── Name pool for NPCs (from the central roster) ────────────────────────
_used_names: list[str] = []


def _pick_name() -> str:
    """Pick a random unique name from the pool, recycling if exhausted."""
    available = [n for n in NPC_NAMES if n not in _used_names]
    if not available:
        _used_names.clear()
        available = list(NPC_NAMES)
    name = random.choice(available)
    _used_names.append(name)
    return name


class NPC:
    """Playable pawn – receives voice/click commands and has an action queue."""

    kind: str = "pawn"
    controllable: bool = True
    _next_id = 1

    def __init__(
        self,
        x: float,
        y: float,
        game_map: "GameMap",
        resources: List[Resource],
        storage: "ResourceStorage",
        all_npcs: Optional[List["NPC"]] = None,
        name: Optional[str] = None,
        hut: Optional[Structure] = None,
    ):
        self.id = NPC._next_id
        NPC._next_id += 1
        self.name = name or _pick_name()

        # position in world pixels
        self.x = x
        self.y = y

        # refs
        self._map = game_map
        self._resources = resources
        self._storage = storage
        self._all_npcs: List["NPC"] = all_npcs if all_npcs is not None else []
        self._wait_counter = 0  # frames spent waiting for a blocked tile
        self._repath_attempts = 0  # consecutive re-paths without progress
        self._hut: Optional[Structure] = hut  # storage hut (deposit point)

        # stats
        self.health = NPC_MAX_HEALTH
        self.max_health = NPC_MAX_HEALTH
        self.speed = NPC_SPEED
        self.hunger = NPC_HUNGER_MAX
        self.max_hunger = NPC_HUNGER_MAX

        # FSM
        self.state = State.IDLE
        self.action_queue: deque[Action] = deque()
        self._current_action: Optional[Action] = None
        self._path: List[Tuple[int, int]] = []
        self._path_index = 0
        self._perform_timer = 0
        self._perform_duration = 0

        # carrying / return-to-hut state
        self.is_carrying: bool = False
        self.carrying: dict[str, int] = {}
        self._last_harvest_action: Optional[ActionType] = None
        self._last_harvest_target: Optional[Resource] = None

        # selection
        self.selected = False

        # speech bubble
        self._speech_text: str = ""
        self._speech_timer: int = 0  # frames remaining

        # visual
        self._radius = 14

    # ── public interface ─────────────────────────────────────────────────

    def say(self, text: str, duration_frames: int = 300):
        """Show a speech bubble above this NPC for *duration_frames* frames."""
        self._speech_text = text
        self._speech_timer = duration_frames

    def enqueue(self, action: Action):
        """Add an action to this NPC's queue."""
        self.action_queue.append(action)
        # kick-start if idle
        if self.state in (State.IDLE, State.DONE):
            self._next_action()

    @property
    def tile_pos(self) -> Tuple[int, int]:
        return self._map.world_to_tile(self.x, self.y)

    @property
    def queue_size(self) -> int:
        return len(self.action_queue) + (1 if self._current_action else 0)

    # ── FSM update ───────────────────────────────────────────────────────

    def update(self):
        """Called every frame."""
        # speech bubble countdown
        if self._speech_timer > 0:
            self._speech_timer -= 1

        # hunger drain
        self.hunger = max(0.0, self.hunger - NPC_HUNGER_DRAIN)
        if self.hunger <= 0:
            self.health = max(0, self.health - NPC_HUNGER_DAMAGE)

        if self.state == State.IDLE:
            if self.action_queue:
                self._next_action()

        elif self.state == State.MOVING:
            self._follow_path()

        elif self.state == State.PERFORMING:
            self._perform()

        elif self.state == State.RETURNING:
            self._follow_path()          # reuses the standard path follower

        elif self.state == State.DONE:
            # finished current action, release reservation and try next
            self._release_reservation()
            self._current_action = None
            if self.action_queue:
                self._next_action()
            else:
                self.state = State.IDLE

    # ── internal FSM helpers ─────────────────────────────────────────────

    def _next_action(self):
        # Must deposit carried resource before starting any new action
        if self.is_carrying:
            self._start_return_to_hut()
            return

        if not self.action_queue:
            self.state = State.IDLE
            return
        # release any previous reservation
        self._release_reservation()
        action = self.action_queue.popleft()
        self._current_action = action

        if action.action_type == ActionType.CHOP_WOOD:
            target = action.target or self._find_nearest(Tree)
            if target is None:
                self.state = State.DONE
                return
            action.target = target
            target.reserved_by = self.id
            self._plan_move_to(target.col, target.row)

        elif action.action_type == ActionType.MINE_ROCK:
            target = action.target or self._find_nearest(Rock)
            if target is None:
                self.state = State.DONE
                return
            action.target = target
            target.reserved_by = self.id
            self._plan_move_to(target.col, target.row)

        elif action.action_type == ActionType.BUILD:
            if isinstance(action.target, Structure):
                # Already have a structure object – walk to an adjacent tile
                adj = self._adjacent_to_structure(action.target)
                if adj is None:
                    self.state = State.DONE
                    return
                self._plan_move_to(*adj)
            else:
                # Resolve location: explicit (col, row) or fallback to NPC tile
                if isinstance(action.target, tuple):
                    col, row = action.target
                else:
                    col, row = self.tile_pos
                # Determine building type grid size
                btype = "house1"
                gw, gh = Structure.GRID_SIZES.get(btype, (2, 2))
                # Find a free area big enough for the multi-tile structure
                resolved = self._find_free_area(col, row, gw, gh)
                if resolved is None:
                    self.say("No space to build!", 120)
                    self.state = State.DONE
                    return
                col, row = resolved
                # Pay resource cost
                if (
                    self._storage.get("wood") < BUILD_COST_WOOD
                    or self._storage.get("stone") < BUILD_COST_STONE
                ):
                    self.state = State.DONE
                    return
                self._storage.spend("wood", BUILD_COST_WOOD)
                self._storage.spend("stone", BUILD_COST_STONE)
                struct = Structure(col, row, building_type=btype)
                self._resources.append(struct)
                action.target = struct
                # Walk to an adjacent tile (not onto the structure)
                adj = self._adjacent_to_structure(struct)
                if adj is None:
                    self._plan_move_to(col, row)
                else:
                    self._plan_move_to(*adj)

        elif action.action_type == ActionType.MOVE_TO:
            if isinstance(action.target, tuple):
                self._plan_move_to(*action.target)
            else:
                self.state = State.DONE

        elif action.action_type == ActionType.EAT:
            # Consume wheat from global storage, no movement needed
            if self._storage.get("wheat") < EAT_WHEAT_COST:
                self.say("No wheat to eat!", 120)
                self.state = State.DONE
                return
            self._storage.spend("wheat", EAT_WHEAT_COST)
            self._perform_timer = 0
            self._perform_duration = NPC_EAT_TIME
            self.state = State.PERFORMING

        elif action.action_type == ActionType.PLANT_WHEAT:
            # Plant a new wheat field at the given tile or NPC's tile
            if isinstance(action.target, tuple):
                col, row = action.target
            else:
                col, row = self.tile_pos
            # Auto-find a nearby valid tile (walkable + no entity)
            resolved = self._find_nearby_free_tile(col, row)
            if resolved is None:
                self.say("No space to plant!", 120)
                self.state = State.DONE
                return
            col, row = resolved
            field = WheatField(col, row)
            self._resources.append(field)
            action.target = field
            self._plan_move_to(col, row)

        elif action.action_type == ActionType.collect_wheat:
            target = action.target or self._find_nearest_ready_wheat()
            if target is None:
                self.say("No wheat ready!", 120)
                self.state = State.DONE
                return
            action.target = target
            self._plan_move_to(target.col, target.row)

    def _plan_move_to(self, col: int, row: int):
        start = self.tile_pos
        blocked = self._occupied_by_npcs() | self._occupied_by_structures()
        path = find_path(self._map, start, (col, row), blocked=blocked)
        if not path:
            self.state = State.DONE
            return
        self._path = path
        self._path_index = 0
        self.state = State.MOVING

    def _follow_path(self):
        if self._path_index >= len(self._path):
            # arrived – deposit if carrying, otherwise normal arrival
            if self.state == State.RETURNING:
                self._deposit_at_hut()
            else:
                self._on_arrival()
            return

        target_col, target_row = self._path[self._path_index]

        # ── NPC-to-NPC tile collision: push blocker immediately ──────
        my_tile = self.tile_pos
        if my_tile != (target_col, target_row) and self._all_npcs:
            for n in self._all_npcs:
                if n.id != self.id and n.tile_pos == (target_col, target_row):
                    self._push_npc_off_tile((target_col, target_row))
                    break

        tx, ty = self._map.tile_center(target_col, target_row)
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)

        if dist < self.speed:
            self.x, self.y = tx, ty
            self._path_index += 1
            self._repath_attempts = 0  # made real progress
        else:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def _on_arrival(self):
        """Arrived at target tile → begin performing or finish."""
        if self._current_action is None:
            self.state = State.DONE
            return

        at = self._current_action.action_type
        if at == ActionType.CHOP_WOOD:
            self._perform_timer = 0
            self._perform_duration = NPC_COLLECT_UNIT_TIME
            self.state = State.PERFORMING
        elif at == ActionType.MINE_ROCK:
            self._perform_timer = 0
            self._perform_duration = NPC_COLLECT_UNIT_TIME
            self.state = State.PERFORMING
        elif at == ActionType.BUILD:
            self._perform_timer = 0
            self._perform_duration = NPC_BUILD_TIME
            self.state = State.PERFORMING
        elif at == ActionType.PLANT_WHEAT:
            self._perform_timer = 0
            self._perform_duration = WHEAT_PLANT_TIME
            self.state = State.PERFORMING
        elif at == ActionType.collect_wheat:
            # Push any NPC blocking the wheat field before harvesting
            target = self._current_action.target
            if target is not None:
                self._push_npc_off_tile((target.col, target.row))
            self._perform_timer = 0
            self._perform_duration = NPC_COLLECT_UNIT_TIME
            self.state = State.PERFORMING
        elif at == ActionType.MOVE_TO:
            self.state = State.DONE
        else:
            self.state = State.DONE

    def _perform(self):
        self._perform_timer += 1

        target = self._current_action.target if self._current_action else None

        # ── Harvest actions: collect 1 unit then carry it back to hut ──
        if isinstance(target, Resource) and not target.depleted:
            if self._current_action.action_type in (
                ActionType.CHOP_WOOD,
                ActionType.MINE_ROCK,
            ):
                if self._perform_timer >= NPC_COLLECT_UNIT_TIME:
                    result = target.collect_one_unit()
                    if result:
                        res_type, amount = result
                        self.is_carrying = True
                        self.carrying = {res_type: amount}
                        self._last_harvest_action = self._current_action.action_type
                        self._last_harvest_target = target
                        self._start_return_to_hut()
                        return
                    else:
                        self.state = State.DONE
                        return
                return  # still working, wait for timer

            elif self._current_action.action_type == ActionType.BUILD:
                if isinstance(target, Structure):
                    target.build_tick()
                    if target.built:
                        self.state = State.DONE
                        return

            elif self._current_action.action_type == ActionType.collect_wheat:
                if isinstance(target, WheatField) and target.fully_grown:
                    if self._perform_timer >= NPC_COLLECT_UNIT_TIME:
                        result = target.collect_one_unit()
                        if result:
                            res_type, amount = result
                            self.is_carrying = True
                            self.carrying = {res_type: amount}
                            self._last_harvest_action = self._current_action.action_type
                            self._last_harvest_target = target
                            self._start_return_to_hut()
                            return
                        else:
                            self.state = State.DONE
                            return
                    return  # still working

        # EAT action completes on timer
        if (
            self._current_action
            and self._current_action.action_type == ActionType.EAT
            and self._perform_timer >= self._perform_duration
        ):
            self.hunger = min(self.max_hunger, self.hunger + NPC_EAT_RESTORE)
            self.say("Mmm, delicious!", 90)
            self.state = State.DONE
            return

        if self._perform_timer >= self._perform_duration:
            self.state = State.DONE

    # ── carry / return-to-hut helpers ────────────────────────────────────

    def _start_return_to_hut(self):
        """Path to the storage hut to deposit carried resources."""
        if self._hut is None:
            # No hut registered – deposit immediately (fallback)
            self._deposit_at_hut()
            return
        adj = self._adjacent_to_structure(self._hut)
        if adj is None:
            self._deposit_at_hut()
            return
        start = self.tile_pos
        blocked = self._occupied_by_npcs() | self._occupied_by_structures()
        path = find_path(self._map, start, adj, blocked=blocked)
        if not path:
            self._deposit_at_hut()
            return
        self._path = path
        self._path_index = 0
        self.state = State.RETURNING

    def _deposit_at_hut(self):
        """Deposit carried resources into global storage and auto-loop."""
        for res_type, amount in self.carrying.items():
            self._storage.add(res_type, amount)
        self.is_carrying = False
        self.carrying = {}

        # Release current reservation (the resource we were harvesting)
        self._release_reservation()

        # If the player queued a new action, honour it
        if self.action_queue:
            self._last_harvest_action = None
            self._last_harvest_target = None
            self._current_action = None
            self._next_action()
            return

        # Auto-loop: go back to the same (or a new) resource
        if self._last_harvest_action:
            action_type = self._last_harvest_action
            target = self._last_harvest_target
            if target and not target.depleted:
                # Re-reserve and head back
                self._current_action = Action(action_type, target=target)
                target.reserved_by = self.id
                self._plan_move_to(target.col, target.row)
            else:
                # Resource depleted – go idle, wait for new orders
                self._last_harvest_action = None
                self._last_harvest_target = None
                self._current_action = None
                self.state = State.IDLE
        else:
            self._current_action = None
            self.state = State.IDLE

    # ── queries ──────────────────────────────────────────────────────────

    def _release_reservation(self):
        """Release the resource reservation held by this NPC, if any."""
        if self._current_action and isinstance(self._current_action.target, Resource):
            target = self._current_action.target
            if target.reserved_by == self.id:
                target.reserved_by = None

    def _occupied_by_npcs(self) -> set[Tuple[int, int]]:
        """Return set of tiles currently occupied by *other* NPCs."""
        return {n.tile_pos for n in self._all_npcs if n.id != self.id}

    def _occupied_by_structures(self) -> set[Tuple[int, int]]:
        """Return set of tiles occupied by non-depleted multi-tile structures."""
        tiles: set[Tuple[int, int]] = set()
        for r in self._resources:
            if r.depleted:
                continue
            if isinstance(r, Structure):
                for t in r.occupied_tiles:
                    tiles.add(t)
            else:
                tiles.add((r.col, r.row))
        return tiles

    def _entity_at_tile(self, col: int, row: int) -> Optional[Resource]:
        """Return the first non-depleted entity sitting on (col, row), or None.
        Supports multi-tile structures."""
        for r in self._resources:
            if r.depleted:
                continue
            if isinstance(r, Structure):
                for dc in range(r.grid_width):
                    for dr in range(r.grid_height):
                        if r.col + dc == col and r.row + dr == row:
                            return r
            else:
                if r.col == col and r.row == row:
                    return r
        return None

    def _find_nearby_free_tile(
        self, col: int, row: int, max_radius: int = 5
    ) -> Optional[Tuple[int, int]]:
        """BFS outward from (col, row) to find the nearest tile that is
        walkable AND has no non-depleted entity on it."""
        from collections import deque as _deque

        visited: set[Tuple[int, int]] = set()
        queue: _deque[Tuple[int, int]] = _deque()
        # Check the origin first
        if (
            self._map.is_walkable(col, row)
            and self._entity_at_tile(col, row) is None
        ):
            return (col, row)
        visited.add((col, row))
        queue.append((col, row))
        while queue:
            c, r = queue.popleft()
            for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nc, nr = c + dc, r + dr
                if (nc, nr) in visited:
                    continue
                if abs(nc - col) > max_radius or abs(nr - row) > max_radius:
                    continue
                visited.add((nc, nr))
                if (
                    self._map.is_walkable(nc, nr)
                    and self._entity_at_tile(nc, nr) is None
                ):
                    return (nc, nr)
                queue.append((nc, nr))
        return None

    def _find_free_area(
        self, col: int, row: int, gw: int, gh: int, max_radius: int = 8
    ) -> Optional[Tuple[int, int]]:
        """BFS to find the nearest origin (c, r) where a gw×gh block of
        tiles is entirely walkable and free of entities."""
        from collections import deque as _deque

        def _area_free(c: int, r: int) -> bool:
            for dc in range(gw):
                for dr in range(gh):
                    tc, tr = c + dc, r + dr
                    if not self._map.is_walkable(tc, tr):
                        return False
                    if self._entity_at_tile(tc, tr) is not None:
                        return False
            return True

        visited: set[Tuple[int, int]] = set()
        queue: _deque[Tuple[int, int]] = _deque()
        if _area_free(col, row):
            return (col, row)
        visited.add((col, row))
        queue.append((col, row))
        while queue:
            c, r = queue.popleft()
            for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nc, nr = c + dc, r + dr
                if (nc, nr) in visited:
                    continue
                if abs(nc - col) > max_radius or abs(nr - row) > max_radius:
                    continue
                visited.add((nc, nr))
                if _area_free(nc, nr):
                    return (nc, nr)
                queue.append((nc, nr))
        return None

    def _adjacent_to_structure(self, struct: Structure) -> Optional[Tuple[int, int]]:
        """Return the nearest walkable tile *cardinally* adjacent to the
        structure footprint (sharing an edge, not diagonal-only), closest
        to the NPC's current position."""
        occupied = set(struct.occupied_tiles)
        candidates: set[Tuple[int, int]] = set()
        # For each occupied tile, check its 4 cardinal neighbours
        for oc, orow in occupied:
            for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nc, nr = oc + dc, orow + dr
                if (nc, nr) in occupied:
                    continue
                if not self._map.is_walkable(nc, nr):
                    continue
                candidates.add((nc, nr))
        if not candidates:
            return None
        mc, mr = self.tile_pos
        return min(candidates, key=lambda p: abs(p[0] - mc) + abs(p[1] - mr))

    def _push_npc_off_tile(self, tile: Tuple[int, int]) -> bool:
        """If another NPC is standing on *tile*, nudge them to an adjacent
        free walkable tile.  Returns True if the tile is now clear."""
        blocker: Optional[NPC] = None
        for n in self._all_npcs:
            if n.id != self.id and n.tile_pos == tile:
                blocker = n
                break
        if blocker is None:
            return True  # already clear

        # find an adjacent walkable tile that isn't occupied by yet another NPC
        occupied = self._occupied_by_npcs()
        for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nc, nr = tile[0] + dc, tile[1] + dr
            if self._map.is_walkable(nc, nr) and (nc, nr) not in occupied:
                # teleport the blocker to the adjacent tile center
                bx, by = self._map.tile_center(nc, nr)
                blocker.x, blocker.y = bx, by
                blocker.say("Excuse me!", 60)
                return True
        return False  # no room to push

    def _find_nearest(self, kind: type) -> Optional[Resource]:
        best: Optional[Resource] = None
        best_dist = float("inf")
        for r in self._resources:
            if isinstance(r, kind) and not r.depleted:
                # skip resources already reserved by another NPC
                if r.reserved_by is not None and r.reserved_by != self.id:
                    continue
                d = abs(r.col - self.tile_pos[0]) + abs(r.row - self.tile_pos[1])
                if d < best_dist:
                    best_dist = d
                    best = r
        return best

    def _find_nearest_ready_wheat(self) -> Optional[WheatField]:
        best: Optional[WheatField] = None
        best_dist = float("inf")
        for r in self._resources:
            if isinstance(r, WheatField) and r.fully_grown and not r.depleted:
                d = abs(r.col - self.tile_pos[0]) + abs(r.row - self.tile_pos[1])
                if d < best_dist:
                    best_dist = d
                    best = r
        return best


# ═══════════════════════════════════════════════════════════════════════════
#  Archer – playable ranged unit
# ═══════════════════════════════════════════════════════════════════════════

_ARCHER_NAMES = ["Robin", "Artemis", "Hawke", "Fletcher", "Ygritte", "Legolas"]
_used_archer_names: list[str] = []


def _pick_archer_name() -> str:
    available = [n for n in _ARCHER_NAMES if n not in _used_archer_names]
    if not available:
        _used_archer_names.clear()
        available = list(_ARCHER_NAMES)
    name = random.choice(available)
    _used_archer_names.append(name)
    return name


class Archer(NPC):
    """Playable archer – same action system as Pawn but uses archer sprites."""

    kind: str = "archer"
    controllable: bool = True

    def __init__(
        self,
        x: float,
        y: float,
        game_map: "GameMap",
        resources: List[Resource],
        storage: "ResourceStorage",
        all_npcs: Optional[List["NPC"]] = None,
        name: Optional[str] = None,
    ):
        super().__init__(
            x, y, game_map, resources, storage,
            all_npcs=all_npcs,
            name=name or _pick_archer_name(),
        )
        self.speed = NPC_SPEED * 1.1  # archers are slightly faster
        self.max_health = 70
        self.health = 70
