"""Pawn: the playable NPC that harvests, builds, farms and eats on order."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from game.actions import PAWN_ACTIONS, Action, ActionType, State
from game.dimensions import ObjectDimensions, find_building_dimensions
from game.entities import Resource, Rock, Structure, Tree, WheatField
from game.npc_base import NPCBase
from game.pathfinding import find_nearest_tile
from game.settings import (
    BUILD_COST_STONE,
    BUILD_COST_WOOD,
    EAT_WHEAT_COST,
    NPC_BUILD_SEARCH_RADIUS,
    NPC_BUILD_TIME,
    NPC_COLLECT_UNIT_TIME,
    NPC_EAT_RESTORE,
    NPC_EAT_TIME,
    NPC_PLANT_SEARCH_RADIUS,
    WHEAT_PLANT_TIME,
)


class NPC(NPCBase):
    """Playable pawn: takes voice and click orders into its action queue."""

    kind: str = "pawn"
    controllable: bool = True
    allowed_actions: list[ActionType] = PAWN_ACTIONS
    _START_BY_ACTION: ClassVar[dict[ActionType, Callable[[NPC, Action], None]]] = {
        ActionType.CHOP_WOOD: lambda npc, action: npc._start_harvest(
            action, Tree, unavailable_message="No trees nearby!"
        ),
        ActionType.MINE_ROCK: lambda npc, action: npc._start_harvest(
            action, Rock, unavailable_message="No rocks nearby!"
        ),
        ActionType.BUILD: lambda npc, action: npc._start_build(action),
        ActionType.MOVE_TO: lambda npc, action: npc._start_move_to(action),
        ActionType.EAT: lambda npc, _action: npc._start_eat(),
        ActionType.PLANT_WHEAT: lambda npc, action: npc._start_plant_wheat(action),
        ActionType.COLLECT_WHEAT: lambda npc, action: npc._start_collect_wheat(action),
    }
    _WORK_TIME_BY_ACTION: ClassVar[dict[ActionType, int]] = {
        ActionType.CHOP_WOOD: NPC_COLLECT_UNIT_TIME,
        ActionType.MINE_ROCK: NPC_COLLECT_UNIT_TIME,
        ActionType.BUILD: NPC_BUILD_TIME,
        ActionType.PLANT_WHEAT: WHEAT_PLANT_TIME,
        ActionType.COLLECT_WHEAT: NPC_COLLECT_UNIT_TIME,
    }

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
        self._start_action(action)

    def _start_action(self, action: Action) -> None:
        self._START_BY_ACTION[action.action_type](self, action)

    def _start_move_to(self, action: Action) -> None:
        if isinstance(action.target, tuple):
            self._plan_move_to(*action.target)
        else:
            self.state = State.DONE

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
        origin = action.target if isinstance(action.target, tuple) else self.tile_pos
        btype = "house1"
        resolved = self._find_free_area(origin, find_building_dimensions(btype))
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
        self._start_performing(NPC_EAT_TIME)

    def _start_plant_wheat(self, action: Action) -> None:
        origin = action.target if isinstance(action.target, tuple) else self.tile_pos
        resolved = find_nearest_tile(
            origin, max_radius=NPC_PLANT_SEARCH_RADIUS, is_suitable=self._is_free_tile
        )
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
        action_type = self.current_action_type
        if action_type is None or action_type not in self._WORK_TIME_BY_ACTION:
            self.state = State.DONE
            return
        self._start_performing(self._WORK_TIME_BY_ACTION[action_type])

    def _perform(self) -> None:
        self._perform_timer += 1
        if self._advance_target_work():
            return
        if self._perform_timer < self._perform_duration:
            return
        if self.current_action_type == ActionType.EAT:
            self._finish_eating()
        else:
            self.state = State.DONE

    def _advance_target_work(self) -> bool:
        """Advance the work on the current action's resource; True when this frame is
        fully handled."""
        action = self._current_action
        if action is None or not isinstance(action.target, Resource) or action.target.depleted:
            return False
        return self._advance_resource_work(action.action_type, action.target)

    def _finish_eating(self) -> None:
        self.hunger = min(self.max_hunger, self.hunger + NPC_EAT_RESTORE)
        self.say("Mmm, delicious!", 90)
        self.state = State.DONE

    def _advance_resource_work(self, action_type: ActionType, target: Resource) -> bool:
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

    def _entity_at_tile(self, tile: tuple[int, int]) -> Resource | None:
        return next(
            (
                resource
                for resource in self._resources
                if not resource.depleted and tile in resource.occupied_tiles
            ),
            None,
        )

    def _is_free_tile(self, tile: tuple[int, int]) -> bool:
        return self._map.is_walkable(*tile) and self._entity_at_tile(tile) is None

    def _find_free_area(
        self, origin: tuple[int, int], dimensions: ObjectDimensions
    ) -> tuple[int, int] | None:
        """Nearest top-left tile, from *origin*, of a footprint whose tiles are all free."""

        def is_footprint_free(corner: tuple[int, int]) -> bool:
            return all(
                self._is_free_tile((corner[0] + dc, corner[1] + dr))
                for dc in range(dimensions.footprint_width)
                for dr in range(dimensions.footprint_depth)
            )

        return find_nearest_tile(
            origin, max_radius=NPC_BUILD_SEARCH_RADIUS, is_suitable=is_footprint_free
        )

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
