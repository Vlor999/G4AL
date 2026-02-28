"""NPC (bot) with Finite-State-Machine, action queue, pathfinding & stats."""

from __future__ import annotations

import math
import random
from collections import deque
from enum import Enum, auto
from typing import List, Tuple, Optional

import pygame

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
    COLOR_NPC_BODY,
    COLOR_NPC_OUTLINE,
    COLOR_NPC_SELECTED,
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
    game_map: "GameMap", start: Tuple[int, int], goal: Tuple[int, int]
) -> List[Tuple[int, int]]:
    """A* on the tile grid. Returns list of (col, row) from start to goal (inclusive)."""
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
    _next_id = 1

    def __init__(
        self,
        x: float,
        y: float,
        game_map: "GameMap",
        resources: List[Resource],
        storage: "ResourceStorage",
        name: Optional[str] = None,
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

        # selection
        self.selected = False

        # speech bubble
        self._speech_text: str = ""
        self._speech_timer: int = 0  # frames remaining

        # visual
        self._radius = 14
        self._bob = 0.0  # idle bobbing animation

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
            self._bob += 0.05
            if self.action_queue:
                self._next_action()

        elif self.state == State.MOVING:
            self._follow_path()

        elif self.state == State.PERFORMING:
            self._perform()

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
                # Already have a structure object – just walk there
                self._plan_move_to(action.target.col, action.target.row)
            else:
                # Resolve location: explicit (col, row) or fallback to NPC tile
                if isinstance(action.target, tuple):
                    col, row = action.target
                else:
                    col, row = self.tile_pos
                # Pay resource cost
                if (
                    self._storage.get("wood") < BUILD_COST_WOOD
                    or self._storage.get("stone") < BUILD_COST_STONE
                ):
                    self.state = State.DONE
                    return
                self._storage.spend("wood", BUILD_COST_WOOD)
                self._storage.spend("stone", BUILD_COST_STONE)
                struct = Structure(col, row)
                self._resources.append(struct)
                action.target = struct
                self._plan_move_to(col, row)

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
            if not self._map.is_walkable(col, row):
                self.state = State.DONE
                return
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
        path = find_path(self._map, start, (col, row))
        if not path:
            self.state = State.DONE
            return
        self._path = path
        self._path_index = 0
        self.state = State.MOVING

    def _follow_path(self):
        if self._path_index >= len(self._path):
            # arrived
            self._on_arrival()
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

    def _on_arrival(self):
        """Arrived at target tile → begin performing or finish."""
        if self._current_action is None:
            self.state = State.DONE
            return

        at = self._current_action.action_type
        if at == ActionType.CHOP_WOOD:
            self._perform_timer = 0
            self._perform_duration = NPC_CHOP_TIME
            self.state = State.PERFORMING
        elif at == ActionType.MINE_ROCK:
            self._perform_timer = 0
            self._perform_duration = NPC_MINE_TIME
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
            self._perform_timer = 0
            self._perform_duration = NPC_CHOP_TIME
            self.state = State.PERFORMING
        elif at == ActionType.MOVE_TO:
            self.state = State.DONE
        else:
            self.state = State.DONE

    def _perform(self):
        self._perform_timer += 1

        target = self._current_action.target if self._current_action else None

        # per-frame work on target
        if isinstance(target, Resource) and not target.depleted:
            if self._current_action.action_type in (
                ActionType.CHOP_WOOD,
                ActionType.MINE_ROCK,
            ):
                result = target.harvest_tick()
                if result:
                    for res, amt in result.items():
                        self._storage.add(res, amt)
                    self.state = State.DONE
                    return
            elif self._current_action.action_type == ActionType.BUILD:
                if isinstance(target, Structure):
                    target.build_tick()
                    if target.built:
                        self.state = State.DONE
                        return
            elif self._current_action.action_type == ActionType.collect_wheat:
                if isinstance(target, WheatField) and target.fully_grown:
                    result = target.harvest_tick()
                    if result:
                        for res, amt in result.items():
                            self._storage.add(res, amt)
                        self.state = State.DONE
                        return

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

    # ── queries ──────────────────────────────────────────────────────────

    def _release_reservation(self):
        """Release the resource reservation held by this NPC, if any."""
        if self._current_action and isinstance(self._current_action.target, Resource):
            target = self._current_action.target
            if target.reserved_by == self.id:
                target.reserved_by = None

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

    # ── drawing ──────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, camera: Tuple[int, int]):
        sx = self.x - camera[0]
        sy = self.y - camera[1]

        # little idle bobbing
        bob_offset = math.sin(self._bob) * 2 if self.state == State.IDLE else 0

        # shadow
        pygame.draw.ellipse(
            surface,
            (0, 0, 0, 80),
            (sx - self._radius, sy + self._radius - 4, self._radius * 2, self._radius),
        )

        # body
        body_y = sy + bob_offset
        outline_color = COLOR_NPC_SELECTED if self.selected else COLOR_NPC_OUTLINE
        pygame.draw.circle(
            surface, outline_color, (int(sx), int(body_y)), self._radius + 2
        )
        pygame.draw.circle(
            surface, COLOR_NPC_BODY, (int(sx), int(body_y)), self._radius
        )

        # tiny face
        eye_y = int(body_y) - 3
        pygame.draw.circle(surface, (50, 50, 50), (int(sx) - 4, eye_y), 2)
        pygame.draw.circle(surface, (50, 50, 50), (int(sx) + 4, eye_y), 2)

        # name label
        name_font = pygame.font.SysFont("consolas", 15, bold=True)
        name_surf = name_font.render(self.name, True, (255, 255, 255))
        name_x = sx - name_surf.get_width() // 2
        name_y = sy - self._radius - 30 + bob_offset
        # dark background for readability
        bg_rect = pygame.Rect(
            name_x - 2,
            name_y - 1,
            name_surf.get_width() + 4,
            name_surf.get_height() + 2,
        )
        bg = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        surface.blit(bg, bg_rect.topleft)
        surface.blit(name_surf, (name_x, name_y))

        # state label (below the name)
        font = pygame.font.SysFont(None, 14)
        label = font.render(self.state.name, True, (200, 200, 200))
        surface.blit(
            label, (sx - label.get_width() // 2, name_y + name_surf.get_height() + 1)
        )

        # HP bar
        if self.health < self.max_health:
            from game.entities import _draw_hp_bar

            _draw_hp_bar(
                surface,
                int(sx),
                int(sy) - self._radius - 26,
                self.health,
                self.max_health,
                28,
            )

        # Hunger bar (always visible, below shadow)
        self._draw_hunger_bar(surface, int(sx), int(sy) + self._radius + 4)

        # speech bubble
        if self._speech_timer > 0 and self._speech_text:
            self._draw_speech_bubble(surface, sx, sy + bob_offset)

    def _draw_hunger_bar(self, surface: pygame.Surface, cx: int, top_y: int):
        """Small hunger bar below the NPC sprite."""
        w, h = 24, 4
        ratio = max(0.0, self.hunger / self.max_hunger)
        bg = pygame.Rect(cx - w // 2, top_y, w, h)
        fg = pygame.Rect(cx - w // 2, top_y, int(w * ratio), h)
        pygame.draw.rect(surface, (60, 60, 60), bg)
        # orange when healthy, red when starving
        bar_color = (255, 152, 0) if ratio > 0.25 else (244, 67, 54)
        pygame.draw.rect(surface, bar_color, fg)

    def _draw_speech_bubble(self, surface: pygame.Surface, sx: float, sy: float):
        """Draw a comic-style speech bubble above the NPC."""
        font = pygame.font.SysFont("consolas", 14)
        max_width = 200
        # word-wrap
        words = self._speech_text.split()
        lines: list[str] = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if font.size(test)[0] > max_width:
                if current:
                    lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)

        line_surfs = [font.render(l, True, (50, 50, 50)) for l in lines]
        padding = 8
        bw = max(s.get_width() for s in line_surfs) + padding * 2
        bh = sum(s.get_height() for s in line_surfs) + padding * 2
        bx = sx - bw // 2
        by = sy - self._radius - 50 - bh

        # bubble background
        bubble_rect = pygame.Rect(int(bx), int(by), bw, bh)
        bubble_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(
            bubble_surf, (255, 255, 240, 230), (0, 0, bw, bh), border_radius=8
        )
        pygame.draw.rect(
            bubble_surf, (180, 170, 140, 200), (0, 0, bw, bh), 2, border_radius=8
        )
        surface.blit(bubble_surf, bubble_rect.topleft)

        # triangle pointer
        tri_cx = int(sx)
        tri_top = int(by + bh)
        pygame.draw.polygon(
            surface,
            (255, 255, 240),
            [(tri_cx - 6, tri_top), (tri_cx + 6, tri_top), (tri_cx, tri_top + 8)],
        )

        # text
        ty = int(by) + padding
        for ls in line_surfs:
            surface.blit(ls, (int(bx) + padding, ty))
            ty += ls.get_height()

    def contains_point(self, wx: float, wy: float) -> bool:
        """Check if world point is inside the NPC sprite."""
        return math.hypot(wx - self.x, wy - self.y) <= self._radius + 4
