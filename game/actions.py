"""Actions an NPC can queue and the states of its action machine."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.entities import Resource


class State(Enum):
    IDLE = auto()
    MOVING = auto()
    PERFORMING = auto()
    RETURNING = auto()
    WAITING_DEPOSIT = auto()
    DONE = auto()


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
        self.target = target
