"""Actions an NPC can queue, the states of its action machine, and the rule that
turns a player order into an action (``create_order_action``)."""

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
    COLLECT_WHEAT = "collect_wheat"
    SHOOT = "shoot"
    DEFEND = "defend"


PAWN_ACTIONS = [
    ActionType.CHOP_WOOD,
    ActionType.MINE_ROCK,
    ActionType.BUILD,
    ActionType.MOVE_TO,
    ActionType.EAT,
    ActionType.PLANT_WHEAT,
    ActionType.COLLECT_WHEAT,
]

ARCHER_ACTIONS = [
    ActionType.MOVE_TO,
    ActionType.SHOOT,
    ActionType.DEFEND,
    ActionType.EAT,
]

TILE_TARGETED_ACTIONS = (ActionType.BUILD, ActionType.PLANT_WHEAT)
"""Actions that work on a tile: without a target they aim at the NPC's own tile."""


class Action:
    """One unit of work for an NPC."""

    def __init__(
        self,
        action_type: ActionType,
        target: Resource | tuple[int, int] | None = None,
    ):
        self.action_type = action_type
        self.target = target


def create_order_action(
    action_type: ActionType,
    *,
    target: tuple[int, int] | None,
    own_tile: tuple[int, int],
) -> Action:
    """Build the action a player order gives an NPC standing on ``own_tile``.

    ``build`` and ``plant_wheat`` aim at ``target``, or at ``own_tile`` without one.
    ``move_to`` aims at ``target``. The other actions ignore it.
    """
    if action_type in TILE_TARGETED_ACTIONS:
        return Action(action_type, target=own_tile if target is None else target)
    if action_type is ActionType.MOVE_TO:
        return Action(action_type, target=target)
    return Action(action_type)
