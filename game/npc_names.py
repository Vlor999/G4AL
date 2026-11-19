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


class NamePool:
    """Names handed out at random, each once, until the pool is exhausted and recycled."""

    def __init__(self, names: Sequence[str]) -> None:
        self._names = tuple(names)
        self._used_names: list[str] = []

    def pick(self) -> str:
        available = [name for name in self._names if name not in self._used_names]
        if not available:
            self._used_names.clear()
            available = list(self._names)
        name = random.choice(available)
        self._used_names.append(name)
        return name


_PAWN_NAMES = NamePool(NPC_NAMES)
_ARCHER_NAMES = NamePool(["Robin", "Artemis", "Hawke", "Fletcher", "Ygritte", "Legolas"])
_WILD_ARCHER_NAMES = NamePool(["Bandit", "Outlaw", "Rogue", "Poacher", "Marauder", "Raider"])


def pick_npc_name() -> str:
    return _PAWN_NAMES.pick()


def pick_archer_name() -> str:
    return _ARCHER_NAMES.pick()


def pick_wild_archer_name() -> str:
    return _WILD_ARCHER_NAMES.pick()
