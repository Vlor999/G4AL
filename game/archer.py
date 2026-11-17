"""Archer: the playable ranged NPC that shoots wild archers."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from game.actions import ARCHER_ACTIONS, Action, ActionType, State
from game.npc import NPC
from game.npc_names import pick_archer_name
from game.settings import (
    ARCHER_ARROW_DAMAGE,
    ARCHER_ARROW_FLIGHT,
    ARCHER_DEFEND_SCAN_RADIUS,
    ARCHER_FIRE_ANIM_TIME,
    ARCHER_RANGE,
    ARCHER_SHOOT_TIME,
    EAT_WHEAT_COST,
    NPC_EAT_RESTORE,
    NPC_EAT_TIME,
    NPC_SPEED,
)

if TYPE_CHECKING:
    from game.creatures import Arrow, Fauna
    from game.entities import Resource
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
        all_npcs: list[NPC] | None = None,
        name: str | None = None,
        all_fauna: list[Fauna] | None = None,
    ):
        super().__init__(
            x,
            y,
            game_map,
            resources,
            storage,
            all_npcs=all_npcs,
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

    def link_battlefield(self, *, fauna: list[Fauna], arrows: list[Arrow]) -> None:
        """Share the world's lists by reference: targets come from *fauna*, shots go to *arrows*."""
        self._all_fauna = fauna
        self._arrows = arrows

    def _find_nearest_enemy(self, max_range: int = 0) -> Fauna | None:
        """Find the nearest living WildArcher in the fauna list.
        If max_range > 0, only consider enemies within that tile distance."""
        best: Fauna | None = None
        best_dist = float("inf")
        mc, mr = self.tile_pos
        for f in self._all_fauna:
            if f.kind != "wild_archer":
                continue
            if f.health <= 0:
                continue
            fc, fr = f.tile_pos
            d = abs(fc - mc) + abs(fr - mr)
            if max_range > 0 and d > max_range:
                continue
            if d < best_dist:
                best_dist = d
                best = f
        return best

    def _enemy_tile_distance(self, enemy: Fauna) -> int:
        mc, mr = self.tile_pos
        ec, er = enemy.tile_pos
        return abs(ec - mc) + abs(er - mr)

    def _pixel_distance(self, enemy: Fauna) -> float:
        return math.hypot(enemy.x - self.x, enemy.y - self.y)

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

        if action.action_type == ActionType.MOVE_TO:
            if isinstance(action.target, tuple):
                self._plan_move_to(*action.target)
            else:
                self.state = State.DONE

        elif action.action_type == ActionType.SHOOT:
            enemy = self._find_nearest_enemy()
            if enemy is None:
                self.say("No enemies!", 90)
                self.state = State.DONE
                return
            self._shoot_target = enemy
            dist = self._enemy_tile_distance(enemy)
            if dist <= ARCHER_RANGE:
                self._start_shoot_perform()
            else:
                self._walk_toward_enemy(enemy)

        elif action.action_type == ActionType.EAT:
            if self._storage.get("wheat") < EAT_WHEAT_COST:
                self.say("No wheat to eat!", 120)
                self.state = State.DONE
                return
            self._storage.spend("wheat", EAT_WHEAT_COST)
            self._perform_timer = 0
            self._perform_duration = NPC_EAT_TIME
            self.state = State.PERFORMING

        elif action.action_type == ActionType.DEFEND:
            self._defending = True
            self.say("Defending!", 90)
            self._defend_scan()

        else:
            self.state = State.DONE

    def _walk_toward_enemy(self, enemy: Fauna) -> None:
        """Pathfind to a tile within ARCHER_RANGE of the enemy."""
        ec, er = enemy.tile_pos
        mc, mr = self.tile_pos
        best_tile: tuple[int, int] | None = None
        best_cost = float("inf")
        for dc in range(-ARCHER_RANGE, ARCHER_RANGE + 1):
            for dr in range(-ARCHER_RANGE, ARCHER_RANGE + 1):
                if abs(dc) + abs(dr) > ARCHER_RANGE:
                    continue
                tc, tr = ec + dc, er + dr
                if not self._map.is_walkable(tc, tr):
                    continue
                cost = abs(tc - mc) + abs(tr - mr)
                if cost < best_cost:
                    best_cost = cost
                    best_tile = (tc, tr)
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
        self._shoot_target = enemy
        dist = self._enemy_tile_distance(enemy)
        if dist <= ARCHER_RANGE:
            self._start_shoot_perform()
        else:
            self._walk_toward_enemy(enemy)

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
                self.say("Target down!", 60)
                self._shoot_target = None
                if self._defending:
                    self._defend_scan()
                else:
                    self.state = State.DONE
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

        if (
            self._current_action
            and self._current_action.action_type == ActionType.EAT
            and self._perform_timer >= self._perform_duration
        ):
            self.hunger = min(self.max_hunger, self.hunger + NPC_EAT_RESTORE)
            self.say("Mmm, delicious!", 90)
            self.state = State.DONE
            return

        if self._current_action and self._current_action.action_type in (
            ActionType.SHOOT,
            ActionType.DEFEND,
        ):
            enemy = self._shoot_target
            if enemy is None or enemy.health <= 0:
                self.say("Target down!", 60)
                self._shoot_target = None
                self._is_firing = False
                if self._defending:
                    self._defend_scan()
                else:
                    self.state = State.DONE
                return

            fire_start = self._perform_duration - ARCHER_FIRE_ANIM_TIME

            if not self._is_firing and self._perform_timer >= fire_start:
                self._is_firing = True
                enemy.health -= ARCHER_ARROW_DAMAGE
                self.say("Fire!", 60)
                if self._arrows is not None:
                    self._arrows.append(
                        {
                            "fromX": self.x,
                            "fromY": self.y - 20,
                            "toX": enemy.x,
                            "toY": enemy.y - 10,
                            "frame": 0,
                            "totalFrames": ARCHER_ARROW_FLIGHT,
                            "team": "blue",
                        }
                    )

            if self._perform_timer >= self._perform_duration:
                self._is_firing = False

                if enemy.health <= 0:
                    self.say("Enemy defeated!", 90)
                    self._shoot_target = None
                    if self._defending:
                        self._defend_scan()
                    else:
                        self.state = State.DONE
                    return

                dist = self._enemy_tile_distance(enemy)
                if dist <= ARCHER_RANGE:
                    self._perform_timer = 0
                else:
                    self._walk_toward_enemy(enemy)
            return

        if self._perform_timer >= self._perform_duration:
            self.state = State.DONE
