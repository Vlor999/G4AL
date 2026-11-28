"""Sheep: fauna that idles, grazes and wanders near where it stands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.fauna.fauna import Fauna
from game.settings import SHEEP_MAX_HEALTH, SHEEP_SPEED

if TYPE_CHECKING:
    from game.world.map import GameMap


class Sheep(Fauna):
    kind = "sheep"
    default_name = "Sheep"
    max_health = SHEEP_MAX_HEALTH
    speed = SHEEP_SPEED

    def __init__(
        self,
        x: float,
        y: float,
        game_map: GameMap,
    ):
        super().__init__(x, y, game_map)
        self._start_idle()
