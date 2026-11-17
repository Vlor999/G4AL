"""Canonical NPC names: the pool new NPCs pick their name from."""

from __future__ import annotations

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
