"""Pawn: the playable NPC that harvests, builds, farms and eats on order."""

from __future__ import annotations

from game.actions import PAWN_ACTIONS, Action, ActionType, State
from game.dimensions import find_building_dimensions
from game.entities import Resource, Rock, Structure, Tree, WheatField
from game.npc_base import NPCBase
from game.settings import (
    BUILD_COST_STONE,
    BUILD_COST_WOOD,
    EAT_WHEAT_COST,
    NPC_BUILD_TIME,
    NPC_COLLECT_UNIT_TIME,
    NPC_EAT_RESTORE,
    NPC_EAT_TIME,
    WHEAT_PLANT_TIME,
)


class NPC(NPCBase):
    """Playable pawn – receives voice/click commands and has an action queue."""

    kind: str = "pawn"
    controllable: bool = True
    allowed_actions: list[ActionType] = PAWN_ACTIONS

    def _next_action(self) -> None:
        if self.is_carrying:
            self._start_return_to_hut()
            return

        if not self.action_queue:
            self.state = State.IDLE
            return
        self._release_reservation()
        action = self.action_queue.popleft()
        self._current_action = action

        if action.action_type == ActionType.CHOP_WOOD:
            self._start_harvest(action, Tree, unavailable_message="No trees nearby!")
        elif action.action_type == ActionType.MINE_ROCK:
            self._start_harvest(action, Rock, unavailable_message="No rocks nearby!")
        elif action.action_type == ActionType.BUILD:
            self._start_build(action)
        elif action.action_type == ActionType.MOVE_TO:
            if isinstance(action.target, tuple):
                self._plan_move_to(*action.target)
            else:
                self.state = State.DONE
        elif action.action_type == ActionType.EAT:
            self._start_eat()
        elif action.action_type == ActionType.PLANT_WHEAT:
            self._start_plant_wheat(action)
        elif action.action_type == ActionType.COLLECT_WHEAT:
            self._start_collect_wheat(action)

    def _start_harvest(
        self, action: Action, kind: type[Resource], *, unavailable_message: str
    ) -> None:
        target = action.target if isinstance(action.target, Resource) else self._find_nearest(kind)
        if target is None:
            self.say(unavailable_message, 120)
            self.state = State.DONE
            return
        action.target = target
        target.reserved_by = self.id
        self._plan_move_to(target.col, target.row)

    def _start_build(self, action: Action) -> None:
        if isinstance(action.target, Structure):
            adj = self._adjacent_to_structure(action.target)
            if adj is None:
                self.state = State.DONE
                return
            self._plan_move_to(*adj)
        else:
            self._start_new_structure(action)

    def _start_new_structure(self, action: Action) -> None:
        if isinstance(action.target, tuple):
            col, row = action.target
        else:
            col, row = self.tile_pos
        btype = "house1"
        dimensions = find_building_dimensions(btype)
        gw, gh = dimensions.footprint_width, dimensions.footprint_depth
        resolved = self._find_free_area(col, row, gw, gh)
        if resolved is None:
            self.say("No space to build!", 120)
            self.state = State.DONE
            return
        col, row = resolved
        if (
            self._storage.get("wood") < BUILD_COST_WOOD
            or self._storage.get("stone") < BUILD_COST_STONE
        ):
            self.say("Not enough resources to build!", 120)
            self.state = State.DONE
            return
        self._storage.spend("wood", BUILD_COST_WOOD)
        self._storage.spend("stone", BUILD_COST_STONE)
        struct = Structure(col, row, building_type=btype)
        self._resources.append(struct)
        action.target = struct
        adj = self._adjacent_to_structure(struct)
        if adj is None:
            self._plan_move_to(col, row)
        else:
            self._plan_move_to(*adj)

    def _start_eat(self) -> None:
        if self._storage.get("wheat") < EAT_WHEAT_COST:
            self.say("No wheat to eat!", 120)
            self.state = State.DONE
            return
        self._storage.spend("wheat", EAT_WHEAT_COST)
        self._perform_timer = 0
        self._perform_duration = NPC_EAT_TIME
        self.state = State.PERFORMING

    def _start_plant_wheat(self, action: Action) -> None:
        if isinstance(action.target, tuple):
            col, row = action.target
        else:
            col, row = self.tile_pos
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

    def _start_collect_wheat(self, action: Action) -> None:
        target = (
            action.target
            if isinstance(action.target, Resource)
            else self._find_nearest_ready_wheat()
        )
        if target is None:
            self.say("No wheat ready!", 120)
            self.state = State.DONE
            return
        action.target = target
        self._plan_move_to(target.col, target.row)

    def _on_arrival(self) -> None:
        if self._current_action is None:
            self.state = State.DONE
            return

        at = self._current_action.action_type
        if at == ActionType.CHOP_WOOD or at == ActionType.MINE_ROCK:
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
        elif at == ActionType.COLLECT_WHEAT:
            self._perform_timer = 0
            self._perform_duration = NPC_COLLECT_UNIT_TIME
            self.state = State.PERFORMING
        elif at == ActionType.MOVE_TO:
            self.state = State.DONE
        else:
            self.state = State.DONE

    def _perform(self) -> None:
        self._perform_timer += 1

        action = self._current_action
        target = action.target if action else None

        if (
            action is not None
            and isinstance(target, Resource)
            and not target.depleted
            and self._advance_resource_work(action.action_type, target)
        ):
            return

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

    def _advance_resource_work(self, action_type: ActionType, target: Resource) -> bool:
        """Advance work on *target*; return True when this frame is fully handled."""
        if action_type in (ActionType.CHOP_WOOD, ActionType.MINE_ROCK):
            self._collect_unit_when_ready(action_type, target)
            return True
        if action_type == ActionType.BUILD:
            if isinstance(target, Structure):
                self._advance_construction(target)
            return True
        if (
            action_type == ActionType.COLLECT_WHEAT
            and isinstance(target, WheatField)
            and target.fully_grown
        ):
            self._collect_unit_when_ready(action_type, target)
            return True
        return False

    def _collect_unit_when_ready(self, action_type: ActionType, target: Resource) -> None:
        if self._perform_timer < NPC_COLLECT_UNIT_TIME:
            return
        result = target.collect_one_unit()
        if result is None:
            self.state = State.DONE
            return
        res_type, amount = result
        self.is_carrying = True
        self.carrying = {res_type: amount}
        self._last_harvest_action = action_type
        self._last_harvest_target = target
        self._start_return_to_hut()

    def _advance_construction(self, target: Structure) -> None:
        # build_tick adds 1 %: tick every NPC_BUILD_TIME/100 frames so the build lasts
        # NPC_BUILD_TIME frames.
        interval = max(1, NPC_BUILD_TIME // 100)
        if self._perform_timer % interval == 0:
            target.build_tick()
        if target.built:
            if target.building_type == "house1":
                self._storage.register_house()
            self.state = State.DONE

    def _entity_at_tile(self, col: int, row: int) -> Resource | None:
        """Return the first non-depleted entity sitting on (col, row), or None.
        Supports multi-tile structures."""
        for r in self._resources:
            if r.depleted:
                continue
            if isinstance(r, Structure):
                for dc in range(r.dimensions.footprint_width):
                    for dr in range(r.dimensions.footprint_depth):
                        if r.col + dc == col and r.row + dr == row:
                            return r
            else:
                if r.col == col and r.row == row:
                    return r
        return None

    def _find_nearby_free_tile(
        self, col: int, row: int, max_radius: int = 5
    ) -> tuple[int, int] | None:
        """BFS outward from (col, row) to find the nearest tile that is
        walkable AND has no non-depleted entity on it."""
        from collections import deque as _deque

        visited: set[tuple[int, int]] = set()
        queue: _deque[tuple[int, int]] = _deque()
        if self._map.is_walkable(col, row) and self._entity_at_tile(col, row) is None:
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
                if self._map.is_walkable(nc, nr) and self._entity_at_tile(nc, nr) is None:
                    return (nc, nr)
                queue.append((nc, nr))
        return None

    def _find_free_area(
        self, col: int, row: int, gw: int, gh: int, max_radius: int = 8
    ) -> tuple[int, int] | None:
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

        visited: set[tuple[int, int]] = set()
        queue: _deque[tuple[int, int]] = _deque()
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

    def _find_nearest(self, kind: type[Resource]) -> Resource | None:
        best: Resource | None = None
        best_dist = float("inf")
        for r in self._resources:
            if isinstance(r, kind) and not r.depleted:
                if r.reserved_by is not None and r.reserved_by != self.id:
                    continue
                d = abs(r.col - self.tile_pos[0]) + abs(r.row - self.tile_pos[1])
                if d < best_dist:
                    best_dist = d
                    best = r
        return best

    def _find_nearest_ready_wheat(self) -> WheatField | None:
        best: WheatField | None = None
        best_dist = float("inf")
        for r in self._resources:
            if isinstance(r, WheatField) and r.fully_grown and not r.depleted:
                d = abs(r.col - self.tile_pos[0]) + abs(r.row - self.tile_pos[1])
                if d < best_dist:
                    best_dist = d
                    best = r
        return best
