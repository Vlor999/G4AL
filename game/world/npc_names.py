"""Name pools of pawns, archers and wild archers, and the picking of a free name."""

from __future__ import annotations

import random
from collections.abc import Sequence
from enum import StrEnum


class NPCName(StrEnum):
    """All available NPC names."""

    BOB = "Bob"
    PAUL = "Paul"
    THOMAS = "Thomas"
    MARIE = "Marie"
    SAM = "Sam"
    LISA = "Lisa"


NPC_NAMES: tuple[str, ...] = tuple(name.value for name in NPCName)
"""Display names of every ``NPCName``, in declaration order (the pick order)."""


class ArcherName(StrEnum):
    ROBIN = "Robin"
    ARTEMIS = "Artemis"
    HAWKE = "Hawke"
    FLETCHER = "Fletcher"
    YGRITTE = "Ygritte"
    LEGOLAS = "Legolas"


ARCHER_NAMES: tuple[str, ...] = tuple(name.value for name in ArcherName)


class WildArcherName(StrEnum):
    BANDIT = "Bandit"
    OUTLAW = "Outlaw"
    ROGUE = "Rogue"
    POACHER = "Poacher"
    MARAUDER = "Marauder"
    RAIDER = "Raider"


WILD_ARCHER_NAMES: tuple[str, ...] = tuple(name.value for name in WildArcherName)


class NamePool:
    """Names drawn from ``rng``, each once, until the pool is exhausted and recycled."""

    def __init__(self, names: Sequence[str], *, rng: random.Random) -> None:
        self._names = tuple(names)
        self._rng = rng
        self._used_names: list[str] = []

    def pick(self) -> str:
        available = [name for name in self._names if name not in self._used_names]
        if not available:
            self._used_names.clear()
            available = list(self._names)
        name = self._rng.choice(available)
        self._used_names.append(name)
        return name


class NamePools:
    """The name pools of one game, all drawing from the same ``rng``."""

    def __init__(self, rng: random.Random) -> None:
        self.pawns = NamePool(NPC_NAMES, rng=rng)
        self.archers = NamePool(ARCHER_NAMES, rng=rng)
        self.wild_archers = NamePool(WILD_ARCHER_NAMES, rng=rng)
