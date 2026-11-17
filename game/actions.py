"""Actions an NPC can queue and the states of its action machine."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.entities import Resource


# ═══════════════════════════════════════════════════════════════════════════
#  FSM States
# ═══════════════════════════════════════════════════════════════════════════


class State(Enum):
    IDLE = auto()
    MOVING = auto()
    PERFORMING = auto()
    RETURNING = auto()  # carrying a resource back to the storage hut
    WAITING_DEPOSIT = auto()  # at the hut, waiting for storage space
    DONE = auto()


# ═══════════════════════════════════════════════════════════════════════════
#  Action descriptors (what goes in the queue)
# ═══════════════════════════════════════════════════════════════════════════


class ActionType(Enum):
    CHOP_WOOD = "chop_wood"
    MINE_ROCK = "mine_rock"
    BUILD = "build"
    MOVE_TO = "move_to"
    EAT = "eat"
    PLANT_WHEAT = "plant_wheat"
    collect_wheat = "collect_wheat"
    SHOOT = "shoot"
    DEFEND = "defend"


# ── Per-unit allowed actions ─────────────────────────────────────────────

PAWN_ACTIONS = [
    ActionType.CHOP_WOOD,
    ActionType.MINE_ROCK,
    ActionType.BUILD,
    ActionType.MOVE_TO,
    ActionType.EAT,
    ActionType.PLANT_WHEAT,
    ActionType.collect_wheat,
]

ARCHER_ACTIONS = [
    ActionType.MOVE_TO,
    ActionType.SHOOT,
    ActionType.DEFEND,
    ActionType.EAT,
]


class Action:
    """One unit of work for an NPC."""

    def __init__(
        self,
        action_type: ActionType,
        target: Resource | tuple[int, int] | None = None,
    ):
        self.action_type = action_type
        self.target = target  # Resource instance or (col, row) for MOVE_TO
