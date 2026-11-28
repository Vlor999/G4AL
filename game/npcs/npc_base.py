"""Shared core of playable NPCs: stats, action queue, path following, hut trips."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from game.npcs.actions import Action, ActionType, State
from game.resources.entities import Resource, Structure
from game.settings import (
    DEFAULT_SPEECH_DURATION_FRAMES,
    LONG_SPEECH_DURATION_FRAMES,
    NPC_HUNGER_DAMAGE,
    NPC_HUNGER_DRAIN,
    NPC_HUNGER_MAX,
    NPC_MAX_HEALTH,
    NPC_SPEED,
)
from game.world.pathfinding import find_path

if TYPE_CHECKING:
    from game.resources.storage import ResourceStorage
    from game.world.map import GameMap


class NPCBase:
    """State, movement and storage trips shared by every playable NPC.

    Subclasses set ``allowed_actions`` and implement ``_next_action``, ``_on_arrival``
    and ``_perform``.
    """

    allowed_actions: list[ActionType]
    _next_id = 1
    # Lambdas, not the base functions, so subclass overrides of each step are called.
    _STEP_BY_STATE: ClassVar[dict[State, Callable[[NPCBase], None]]] = {
        State.IDLE: lambda npc: npc._resume_queue(),
        State.MOVING: lambda npc: npc._follow_path(),
        State.PERFORMING: lambda npc: npc._perform(),
        State.RETURNING: lambda npc: npc._follow_path(),
        State.WAITING_DEPOSIT: lambda npc: npc._retry_deposit(),
        State.DONE: lambda npc: npc._finish_action(),
    }

    def __init__(
        self,
        x: float,
        y: float,
        game_map: GameMap,
        resources: list[Resource],
        storage: ResourceStorage,
        name: str | None = None,
        hut: Structure | None = None,
    ):
        self.id = NPCBase._next_id
        NPCBase._next_id += 1
        self.name = name or game_map.name_pools.pawns.pick()

        self.x = x
        self.y = y

        self._map = game_map
        self._resources = resources
        self._storage = storage
        self._hut: Structure | None = hut

        self.health: float = NPC_MAX_HEALTH
        self.max_health = NPC_MAX_HEALTH
        self.speed = NPC_SPEED
        self.hunger: float = NPC_HUNGER_MAX
        self.max_hunger = NPC_HUNGER_MAX

        self.state = State.IDLE
        self.action_queue: deque[Action] = deque()
        self._current_action: Action | None = None
        self._path: list[tuple[int, int]] = []
        self._path_index = 0
        self._perform_timer = 0
        self._perform_duration = 0

        self.is_carrying: bool = False
        self.carrying: dict[str, int] = {}
        self._last_harvest_action: ActionType | None = None
        self._last_harvest_target: Resource | None = None

        self.selected = False

        self._speech_text: str = ""
        self._speech_timer: int = 0  # frames

    def say(self, text: str, duration_frames: int = DEFAULT_SPEECH_DURATION_FRAMES) -> None:
        """Show a speech bubble above this NPC for *duration_frames* frames."""
        self._speech_text = text
        self._speech_timer = duration_frames

    def enqueue(self, action: Action) -> bool:
        """Add an action to this NPC's queue (validates allowed actions).

        Returns True if the action was accepted, False if rejected.
        """
        if action.action_type not in self.allowed_actions:
            self.say("I can't do that!", LONG_SPEECH_DURATION_FRAMES)
            return False
        self.action_queue.append(action)
        if self.state in (State.IDLE, State.DONE):
            self._next_action()
        return True

    def give_up_waiting_deposit(self) -> bool:
        """Drop the carried load and go idle if waiting for storage space.

        Returns False, changing nothing, when the NPC is not waiting to deposit.
        """
        if self.state != State.WAITING_DEPOSIT:
            return False
        self.is_carrying = False
        self.carrying = {}
        self._last_harvest_action = None
        self._last_harvest_target = None
        self._current_action = None
        self.state = State.IDLE
        return True

    @property
    def tile_pos(self) -> tuple[int, int]:
        return self._map.world_to_tile(self.x, self.y)

    @property
    def current_action_type(self) -> ActionType | None:
        """Type of the action under way; None when no action is under way (idle)."""
        return self._current_action.action_type if self._current_action else None

    @property
    def visible_speech_text(self) -> str:
        """The speech bubble text while it shows, else an empty string."""
        return self._speech_text if self._speech_timer > 0 else ""

    @property
    def is_firing(self) -> bool:
        """True while the shot animation is active; this default means the kind never shoots."""
        return False

    @property
    def is_defending(self) -> bool:
        """True while defend mode is on; this default means the kind never defends."""
        return False

    def update(self) -> None:
        """Advance speech, hunger and the action machine by one frame."""
        self._drain_needs()
        self._STEP_BY_STATE[self.state](self)

    def _drain_needs(self) -> None:
        if self._speech_timer > 0:
            self._speech_timer -= 1
        self.hunger = max(0.0, self.hunger - NPC_HUNGER_DRAIN)
        if self.hunger <= 0:
            self.health = max(0, self.health - NPC_HUNGER_DAMAGE)

    def _resume_queue(self) -> None:
        if self.action_queue:
            self._next_action()

    def _retry_deposit(self) -> None:
        if not self._storage.is_full:
            self._deposit_at_hut()

    def _finish_action(self) -> None:
        self._release_reservation()
        self._current_action = None
        if self.action_queue:
            self._next_action()
        else:
            self.state = State.IDLE

    def _next_action(self) -> None:
        """Start the next queued action, or head to the hut first when carrying a load.

        An override sets ``state`` and, when it pops an action, stores it in
        ``_current_action``.
        """
        raise NotImplementedError

    def _on_arrival(self) -> None:
        """Called when a path ends outside a hut trip. An override sets ``state``."""
        raise NotImplementedError

    def _perform(self) -> None:
        """Called every frame in PERFORMING.

        An override advances ``_perform_timer`` and sets ``state`` when the work ends.
        """
        raise NotImplementedError

    def _start_performing(self, duration: int) -> None:
        """Enter PERFORMING for *duration* frames, counted by ``_perform_timer`` from 0."""
        self._perform_timer = 0
        self._perform_duration = duration
        self.state = State.PERFORMING

    def _plan_move_to(self, col: int, row: int) -> None:
        start = self.tile_pos
        blocked = self._find_tiles_covered_by_resources()
        path = find_path(self._map, start, goal=(col, row), blocked=blocked)
        if not path:
            self.state = State.DONE
            return
        self._path = path
        self._path_index = 0
        self.state = State.MOVING

    def _follow_path(self) -> None:
        if self._path_index >= len(self._path):
            if self.state == State.RETURNING:
                self._deposit_at_hut()
            else:
                self._on_arrival()
            return

        target_col, target_row = self._path[self._path_index]

        center_x, center_y = self._map.tile_center(target_col, target_row)
        dx, dy = center_x - self.x, center_y - self.y
        distance = math.hypot(dx, dy)

        if distance < self.speed:
            self.x, self.y = center_x, center_y
            self._path_index += 1
        else:
            self.x += dx / distance * self.speed
            self.y += dy / distance * self.speed

    def _start_return_to_hut(self) -> None:
        """Path to the storage hut to deposit carried resources."""
        if self._hut is None:
            self._deposit_at_hut()
            return
        hut_side_tile = self._adjacent_to_structure(self._hut)
        if hut_side_tile is None:
            self._deposit_at_hut()
            return
        start = self.tile_pos
        blocked = self._find_tiles_covered_by_resources()
        path = find_path(self._map, start, goal=hut_side_tile, blocked=blocked)
        if not path:
            self._deposit_at_hut()
            return
        self._path = path
        self._path_index = 0
        self.state = State.RETURNING

    def _deposit_at_hut(self) -> None:
        """Deposit the carried load into storage and auto-loop.

        What does not fit stays in ``carrying`` and the NPC waits in
        ``WAITING_DEPOSIT`` until storage has room for it.
        """
        self._store_carried_load()
        self._release_reservation()

        if self.is_carrying:
            self.say("Storage full!", LONG_SPEECH_DURATION_FRAMES)
            self.state = State.WAITING_DEPOSIT
            return

        if self.action_queue:
            self._last_harvest_action = None
            self._last_harvest_target = None
            self._current_action = None
            self._next_action()
            return

        if self._storage.is_full:
            self.say("Storage full!", LONG_SPEECH_DURATION_FRAMES)
            self.state = State.WAITING_DEPOSIT
            return

        if self._last_harvest_action:
            action_type = self._last_harvest_action
            target = self._last_harvest_target
            if target and not target.depleted:
                self._current_action = Action(action_type, target=target)
                target.reserved_by = self.id
                self._plan_move_to(target.col, target.row)
            else:
                self._last_harvest_action = None
                self._last_harvest_target = None
                self._current_action = None
                self.state = State.IDLE
        else:
            self._current_action = None
            self.state = State.IDLE

    def _store_carried_load(self) -> None:
        """Move the carried load into storage, keeping in ``carrying`` what does not fit."""
        kept: dict[str, int] = {}
        for resource_type, amount in self.carrying.items():
            left = amount - self._storage.add(resource_type, amount)
            if left > 0:
                kept[resource_type] = left
        self.carrying = kept
        self.is_carrying = bool(kept)

    def _release_reservation(self) -> None:
        """Release the resource reservation held by this NPC, if any."""
        if self._current_action and isinstance(self._current_action.target, Resource):
            target = self._current_action.target
            if target.reserved_by == self.id:
                target.reserved_by = None

    def _find_tiles_covered_by_resources(self) -> set[tuple[int, int]]:
        """Every tile a non-depleted resource covers, structure footprints included."""
        return {
            tile
            for resource in self._resources
            if not resource.depleted
            for tile in resource.occupied_tiles
        }

    def _adjacent_to_structure(self, structure: Structure) -> tuple[int, int] | None:
        """The walkable tile sharing an edge with the footprint of *structure* that is
        closest to this NPC; None when no such tile exists."""
        occupied = set(structure.occupied_tiles)
        candidates: set[tuple[int, int]] = set()
        for footprint_col, footprint_row in occupied:
            for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (footprint_col + dc, footprint_row + dr)
                if neighbor in occupied:
                    continue
                if not self._map.is_walkable(*neighbor):
                    continue
                candidates.add(neighbor)
        if not candidates:
            return None
        own_col, own_row = self.tile_pos
        return min(candidates, key=lambda tile: abs(tile[0] - own_col) + abs(tile[1] - own_row))
