"""Cat: fauna that never leaves its tile; the client animates it."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.fauna import Fauna

if TYPE_CHECKING:
    from game.entities import Resource
    from game.map import GameMap


class Cat(Fauna):
    kind = "cat"

    def __init__(
        self,
        x: float,
        y: float,
        game_map: GameMap,
        resources: list[Resource],
    ):
        super().__init__(x, y, game_map, resources, name="Le Chat")
        self.speed = 0.0
        self.health = 50
        self.max_health = 50

    def update(self) -> None:
        pass
