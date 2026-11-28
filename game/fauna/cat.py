"""Cat: fauna that never leaves its tile; the client animates it."""

from __future__ import annotations

from game.fauna.fauna import Fauna
from game.settings import CAT_MAX_HEALTH, CAT_SPEED


class Cat(Fauna):
    kind = "cat"
    default_name = "Le Chat"
    max_health = CAT_MAX_HEALTH
    speed = CAT_SPEED

    def update(self) -> None:
        pass
