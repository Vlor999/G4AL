"""Canonical NPC names and the picking of a free one for each new NPC."""

from __future__ import annotations

import random
from enum import Enum


class NPCName(Enum):
    """All available NPC names."""

    BOB = "Bob"
    PAUL = "Paul"
    THOMAS = "Thomas"
    MARIE = "Marie"
    SAM = "Sam"
    LISA = "Lisa"


NPC_NAMES: tuple[str, ...] = tuple(name.value for name in NPCName)
"""Display names of every ``NPCName``, in declaration order (the pick order)."""

_used_names: list[str] = []


def pick_npc_name() -> str:
    """Pick a random unique name from the pool, recycling if exhausted."""
    available = [n for n in NPC_NAMES if n not in _used_names]
    if not available:
        _used_names.clear()
        available = list(NPC_NAMES)
    name = random.choice(available)
    _used_names.append(name)
    return name


_ARCHER_NAMES = ["Robin", "Artemis", "Hawke", "Fletcher", "Ygritte", "Legolas"]
_used_archer_names: list[str] = []


def pick_archer_name() -> str:
    available = [n for n in _ARCHER_NAMES if n not in _used_archer_names]
    if not available:
        _used_archer_names.clear()
        available = list(_ARCHER_NAMES)
    name = random.choice(available)
    _used_archer_names.append(name)
    return name
