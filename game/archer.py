"""Archer: the playable ranged NPC that shoots wild archers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.actions import ARCHER_ACTIONS, Action, ActionType, State
from game.arrows import Team, build_arrow
from game.npc import NPC
from game.npc_names import pick_archer_name
from game.settings import (
    ARCHER_ARROW_DAMAGE,
    ARCHER_DEFEND_SCAN_RADIUS,
    ARCHER_FIRE_ANIM_TIME,
    ARCHER_RANGE,
    ARCHER_SHOOT_TIME,
    NPC_EAT_RESTORE,
    NPC_SPEED,
)
from game.targeting import find_nearest_living, find_walkable_tile_in_range, tile_distance

if TYPE_CHECKING:
    from game.arrows import Arrow
    from game.entities import Resource
    from game.fauna import Fauna
    from game.map import GameMap
    from game.storage import ResourceStorage


class Archer(NPC):
    """Playable archer – ranged unit with shoot action."""

    kind: str = "archer"
    controllable: bool = True
    allowed_actions: list[ActionType] = ARCHER_ACTIONS

    def __init__(
        self,
        x: float,
        y: float,
        game_map: GameMap,
        resources: list[Resource],
        storage: ResourceStorage,
        name: str | None = None,
        all_fauna: list[Fauna] | None = None,
    ):
        super().__init__(
            x,
            y,
            game_map,
            resources,
            storage,
            name=name or pick_archer_name(),
        )
        self.speed = NPC_SPEED * 1.1
        self.max_health = 70
        self.health = 70
        self._all_fauna: list[Fauna] = all_fauna if all_fauna is not None else []
        self._shoot_target: Fauna | None = None
        self._arrows: list[Arrow] = []
        self._is_firing: bool = False
        self._defending: bool = False

    @property
    def is_firing(self) -> bool:
        return self._is_firing

    @property
    def is_defending(self) -> bool:
        return self._defending

    def link_battlefield(self, *, fauna: list[Fauna], arrows: list[Arrow]) -> None:
        """Share the world's lists by reference: targets come from *fauna*, shots go to *arrows*."""
        self._all_fauna = fauna
        self._arrows = arrows

    def _find_nearest_enemy(self, max_range: int | None = None) -> Fauna | None:
        wild_archers = (creature for creature in self._all_fauna if creature.kind == "wild_archer")
        return find_nearest_living(self.tile_pos, wild_archers, max_distance=max_range)

    def _enemy_tile_distance(self, enemy: Fauna) -> int:
        return tile_distance(self.tile_pos, enemy.tile_pos)

    def enqueue(self, action: Action) -> bool:
        """Override: cancel defend mode when a new action is enqueued."""
        self._defending = False
        self._shoot_target = None
        self._is_firing = False
        return super().enqueue(action)

    def update(self) -> None:
        """Override: while defending and idle, keep scanning for enemies."""
        super().update()
        if self._defending and self.state == State.IDLE and not self.action_queue:
            self._defend_scan()

    def _next_action(self) -> None:
        """Start a queued MOVE_TO, SHOOT, EAT or DEFEND; any other action ends DONE."""
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
        if action.action_type == ActionType.MOVE_TO:
            self._start_move_to(action)
        elif action.action_type == ActionType.SHOOT:
            self._start_shooting()
        elif action.action_type == ActionType.EAT:
            self._start_eat()
        elif action.action_type == ActionType.DEFEND:
            self._start_defending()
        else:
            self.state = State.DONE

    def _start_move_to(self, action: Action) -> None:
        if isinstance(action.target, tuple):
            self._plan_move_to(*action.target)
        else:
            self.state = State.DONE

    def _start_shooting(self) -> None:
        enemy = self._find_nearest_enemy()
        if enemy is None:
            self.say("No enemies!", 90)
            self.state = State.DONE
            return
        self._engage(enemy)

    def _start_defending(self) -> None:
        self._defending = True
        self.say("Defending!", 90)
        self._defend_scan()

    def _engage(self, enemy: Fauna) -> None:
        """Shoot *enemy* from here when in range, else walk into range first."""
        self._shoot_target = enemy
        if self._enemy_tile_distance(enemy) <= ARCHER_RANGE:
            self._start_shoot_perform()
        else:
            self._walk_toward_enemy(enemy)

    def _walk_toward_enemy(self, enemy: Fauna) -> None:
        """Pathfind to a tile within ARCHER_RANGE of the enemy."""
        best_tile = find_walkable_tile_in_range(
            self._map, origin=self.tile_pos, target=enemy.tile_pos, shooting_range=ARCHER_RANGE
        )
        if best_tile is None:
            self.say("Can't reach enemy!", 90)
            self.state = State.DONE
            return
        self._plan_move_to(*best_tile)

    def _defend_scan(self) -> None:
        """Scan for enemies within defend radius and engage if found."""
        enemy = self._find_nearest_enemy(max_range=ARCHER_DEFEND_SCAN_RADIUS)
        if enemy is None:
            self.state = State.IDLE
            return
        self._engage(enemy)

    def _start_shoot_perform(self) -> None:
        self._perform_timer = 0
        self._perform_duration = ARCHER_SHOOT_TIME
        self._is_firing = False
        self.state = State.PERFORMING

    def _on_arrival(self) -> None:
        """Override: after walking toward enemy, start shooting."""
        if (
            self._current_action
            and self._current_action.action_type in (ActionType.SHOOT, ActionType.DEFEND)
            and self._shoot_target is not None
        ):
            enemy = self._shoot_target
            if enemy.health <= 0:
                self._lose_target()
                return
            dist = self._enemy_tile_distance(enemy)
            if dist <= ARCHER_RANGE:
                self._start_shoot_perform()
            else:
                self._walk_toward_enemy(enemy)
            return

        if self._current_action and self._current_action.action_type == ActionType.MOVE_TO:
            self.state = State.DONE
            return

        self.state = State.DONE

    def _perform(self) -> None:
        self._perform_timer += 1
        action_type = self.current_action_type
        if action_type == ActionType.EAT and self._perform_timer >= self._perform_duration:
            self._finish_eating()
            return
        if action_type in (ActionType.SHOOT, ActionType.DEFEND):
            self._advance_shot()
            return
        if self._perform_timer >= self._perform_duration:
            self.state = State.DONE

    def _finish_eating(self) -> None:
        self.hunger = min(self.max_hunger, self.hunger + NPC_EAT_RESTORE)
        self.say("Mmm, delicious!", 90)
        self.state = State.DONE

    def _advance_shot(self) -> None:
        """Aim, release the arrow at the end of the cycle, then shoot again or follow."""
        enemy = self._shoot_target
        if enemy is None or enemy.health <= 0:
            self._is_firing = False
            self._lose_target()
            return
        fire_start = self._perform_duration - ARCHER_FIRE_ANIM_TIME
        if not self._is_firing and self._perform_timer >= fire_start:
            self._release_arrow(enemy)
        if self._perform_timer >= self._perform_duration:
            self._end_shot_cycle(enemy)

    def _release_arrow(self, enemy: Fauna) -> None:
        self._is_firing = True
        enemy.health -= ARCHER_ARROW_DAMAGE
        self.say("Fire!", 60)
        self._arrows.append(build_arrow(shooter=self, target=enemy, team=Team.BLUE))

    def _end_shot_cycle(self, enemy: Fauna) -> None:
        self._is_firing = False
        if self._enemy_tile_distance(enemy) <= ARCHER_RANGE:
            self._perform_timer = 0
        else:
            self._walk_toward_enemy(enemy)

    def _lose_target(self) -> None:
        """The target is down: watch for the next one when defending, else end the order."""
        self.say("Target down!", 60)
        self._shoot_target = None
        if self._defending:
            self._defend_scan()
        else:
            self.state = State.DONE
