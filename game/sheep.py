"""Sheep: fauna that idles, grazes and wanders near where it stands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.fauna import Fauna

if TYPE_CHECKING:
    from game.entities import Resource
    from game.map import GameMap


class Sheep(Fauna):
    kind = "sheep"

    def __init__(
        self,
        x: float,
        y: float,
        game_map: GameMap,
        resources: list[Resource],
    ):
        super().__init__(x, y, game_map, resources, name="Sheep")
        self.speed = 0.8
        self.health = 20
        self.max_health = 20
        self._start_idle()
