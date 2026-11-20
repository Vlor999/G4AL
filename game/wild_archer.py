"""Wild archer: hostile fauna of the red team that shoots pawns and archers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.arrows import Arrow, Team, build_arrow
from game.fauna import Fauna, FaunaState
from game.settings import (
    ARCHER_FIRE_ANIM_TIME,
    WILD_ARCHER_DAMAGE,
    WILD_ARCHER_RANGE,
    WILD_ARCHER_SHOOT_TIME,
)
from game.targeting import find_nearest_living, find_walkable_tile_in_range, tile_distance

if TYPE_CHECKING:
    from game.entities import Resource
    from game.map import GameMap
    from game.npc import NPC


class WildArcher(Fauna):
    """Red-team fauna that patrols, chases the pawns and archers near it and shoots them."""

    kind = "wild_archer"
    wander_radius = 8

    def __init__(
        self,
        x: float,
        y: float,
        game_map: GameMap,
        resources: list[Resource],
    ):
        super().__init__(x, y, game_map, resources, name=game_map.name_pools.wild_archers.pick())
        self.speed = 1.5
        self.health = 50
        self.max_health = 50
        self._shoot_duration = 0
        self._attack_target: NPC | None = None
        self._all_npcs: list[NPC] = []
        self._arrows: list[Arrow] = []
        self._is_firing: bool = False
        self._start_idle()

    @property
    def is_firing(self) -> bool:
        return self._is_firing

    def link_battlefield(self, *, npcs: list[NPC], arrows: list[Arrow]) -> None:
        """Share the world's lists by reference: targets come from *npcs*, shots go to *arrows*."""
        self._all_npcs = npcs
        self._arrows = arrows

    def update(self) -> None:
        if self.health <= 0:
            return
        if self.state == FaunaState.IDLE:
            self._do_idle()
        elif self.state == FaunaState.WANDERING:
            self._do_wander()
        elif self.state == FaunaState.SHOOTING:
            self._do_shoot()

    def _find_nearest_npc(self) -> tuple[NPC | None, float]:
        target = find_nearest_living(self.tile_pos, self._all_npcs)
        if target is None:
            return None, float("inf")
        return target, tile_distance(self.tile_pos, target.tile_pos)

    def _do_idle(self) -> None:
        self._timer += 1
        if self._timer >= self._idle_duration:
            self._timer = 0
            target, dist = self._find_nearest_npc()
            if target and dist <= WILD_ARCHER_RANGE:
                self._attack_target = target
                self._start_shoot()
                return
            if target and dist <= 6:
                self._chase_target(target)
                return
            roll = self._map.rng.random()
            if roll < 0.35:
                self._start_wander()
            else:
                self._idle_duration = self._map.rng.randint(90, 300)

    def _do_wander(self) -> None:
        if self._path_index >= len(self._path):
            self._start_idle()
            return
        target, dist = self._find_nearest_npc()
        if target and dist <= WILD_ARCHER_RANGE:
            self._attack_target = target
            self._start_shoot()
            return
        self._follow_path()

    def _chase_target(self, target: NPC) -> None:
        best_tile = find_walkable_tile_in_range(
            self._map,
            origin=self.tile_pos,
            target=target.tile_pos,
            shooting_range=WILD_ARCHER_RANGE,
        )
        if best_tile is None:
            self._start_idle()
            return
        self._walk_to(best_tile)

    def _start_shoot(self) -> None:
        self.state = FaunaState.SHOOTING
        self._timer = 0
        self._shoot_duration = WILD_ARCHER_SHOOT_TIME
        self._is_firing = False

    def _do_shoot(self) -> None:
        self._timer += 1
        target = self._attack_target
        if target is None or target.health <= 0:
            self._attack_target = None
            self._is_firing = False
            self._start_idle()
            return

        fire_start = self._shoot_duration - ARCHER_FIRE_ANIM_TIME

        if not self._is_firing and self._timer >= fire_start:
            self._is_firing = True
            dist = tile_distance(self.tile_pos, target.tile_pos)
            if dist > WILD_ARCHER_RANGE:
                self._attack_target = None
                self._is_firing = False
                self._start_idle()
                return
            target.health = max(0, target.health - WILD_ARCHER_DAMAGE)
            self._arrows.append(build_arrow(shooter=self, target=target, team=Team.RED))

        if self._timer >= self._shoot_duration:
            self._is_firing = False
            if target.health > 0:
                self._timer = 0
            else:
                self._attack_target = None
                self._start_idle()
