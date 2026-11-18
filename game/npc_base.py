"""Shared core of playable NPCs: stats, action queue, path following, hut trips."""

from __future__ import annotations

import math
from collections import deque
from typing import TYPE_CHECKING

from game.actions import Action, ActionType, State
from game.entities import Resource, Structure
from game.npc_names import pick_npc_name
from game.pathfinding import find_path
from game.settings import (
    NPC_HUNGER_DAMAGE,
    NPC_HUNGER_DRAIN,
    NPC_HUNGER_MAX,
    NPC_MAX_HEALTH,
    NPC_SPEED,
)

if TYPE_CHECKING:
    from game.map import GameMap
    from game.storage import ResourceStorage


class NPCBase:
    """State, movement and storage trips shared by every playable NPC.

    Subclasses set ``allowed_actions`` and implement ``_next_action``, ``_on_arrival``
    and ``_perform``.
    """

    allowed_actions: list[ActionType]
    _next_id = 1

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
        self.name = name or pick_npc_name()

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

    def say(self, text: str, duration_frames: int = 300) -> None:
        """Show a speech bubble above this NPC for *duration_frames* frames."""
        self._speech_text = text
        self._speech_timer = duration_frames

    def enqueue(self, action: Action) -> bool:
        """Add an action to this NPC's queue (validates allowed actions).

        Returns True if the action was accepted, False if rejected.
        """
        if action.action_type not in self.allowed_actions:
            self.say("I can't do that!", 180)
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
    def queue_size(self) -> int:
        return len(self.action_queue) + (1 if self._current_action else 0)

    def update(self) -> None:
        """Called every frame."""
        if self._speech_timer > 0:
            self._speech_timer -= 1

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
            self._follow_path()

        elif self.state == State.WAITING_DEPOSIT:
            if not self._storage.is_full:
                self._deposit_at_hut()

        elif self.state == State.DONE:
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

    def _plan_move_to(self, col: int, row: int) -> None:
        start = self.tile_pos
        blocked = self._occupied_by_structures()
        path = find_path(self._map, start, (col, row), blocked=blocked)
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

        tx, ty = self._map.tile_center(target_col, target_row)
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)

        if dist < self.speed:
            self.x, self.y = tx, ty
            self._path_index += 1
        else:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def _start_return_to_hut(self) -> None:
        """Path to the storage hut to deposit carried resources."""
        if self._hut is None:
            self._deposit_at_hut()
            return
        adj = self._adjacent_to_structure(self._hut)
        if adj is None:
            self._deposit_at_hut()
            return
        start = self.tile_pos
        blocked = self._occupied_by_structures()
        path = find_path(self._map, start, adj, blocked=blocked)
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
            self.say("Storage full!", 180)
            self.state = State.WAITING_DEPOSIT
            return

        if self.action_queue:
            self._last_harvest_action = None
            self._last_harvest_target = None
            self._current_action = None
            self._next_action()
            return

        if self._storage.is_full:
            self.say("Storage full!", 180)
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
        for res_type, amount in self.carrying.items():
            left = amount - self._storage.add(res_type, amount)
            if left > 0:
                kept[res_type] = left
        self.carrying = kept
        self.is_carrying = bool(kept)

    def _release_reservation(self) -> None:
        """Release the resource reservation held by this NPC, if any."""
        if self._current_action and isinstance(self._current_action.target, Resource):
            target = self._current_action.target
            if target.reserved_by == self.id:
                target.reserved_by = None

    def _occupied_by_structures(self) -> set[tuple[int, int]]:
        """Return set of tiles occupied by non-depleted multi-tile structures."""
        tiles: set[tuple[int, int]] = set()
        for r in self._resources:
            if r.depleted:
                continue
            if isinstance(r, Structure):
                for t in r.occupied_tiles:
                    tiles.add(t)
            else:
                tiles.add((r.col, r.row))
        return tiles

    def _adjacent_to_structure(self, struct: Structure) -> tuple[int, int] | None:
        """Return the nearest walkable tile *cardinally* adjacent to the
        structure footprint (sharing an edge, not diagonal-only), closest
        to the NPC's current position."""
        occupied = set(struct.occupied_tiles)
        candidates: set[tuple[int, int]] = set()
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
