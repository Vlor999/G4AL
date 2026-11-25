"""Cat: fauna that never leaves its tile; the client animates it."""

from __future__ import annotations

from game.fauna import Fauna


class Cat(Fauna):
    kind = "cat"
    default_name = "Le Chat"
    max_health = 50
    speed = 0.0

    def update(self) -> None:
        pass
