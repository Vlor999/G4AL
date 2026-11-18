"""Orders the player gives one NPC directly, with the mouse or an action button."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from game.actions import Action, ActionType
from game.map import GameMap
from game.npc import NPC


class DirectOrderOutcome(StrEnum):
    """What became of a direct order."""

    ACCEPTED = "accepted"
    REFUSED_BY_NPC = "refused_by_npc"
    UNKNOWN_NPC = "unknown_npc"
    TARGET_OUTSIDE_MAP = "target_outside_map"


@dataclass(frozen=True)
class DirectOrder:
    """One action for the NPC ``npc_id``, aimed at the ``(col, row)`` tile ``target``.

    ``move_to`` needs a target. ``build`` and ``plant_wheat`` without one aim at the
    NPC's own tile; the other actions ignore it.
    """

    npc_id: int
    action_type: ActionType
    target: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.action_type == ActionType.MOVE_TO and self.target is None:
            raise ValueError("move_to needs a target tile")


def apply_direct_order(
    order: DirectOrder, *, npcs: Sequence[NPC], game_map: GameMap
) -> DirectOrderOutcome:
    """Enqueue ``order`` on its NPC and return what became of it.

    The NPC itself refuses an action it is not allowed to do, and says so in the game.
    """
    if order.target is not None and not game_map.contains_tile(*order.target):
        return DirectOrderOutcome.TARGET_OUTSIDE_MAP
    npc = next((npc for npc in npcs if npc.id == order.npc_id), None)
    if npc is None:
        return DirectOrderOutcome.UNKNOWN_NPC
    if npc.enqueue(_action_for(npc, order)):
        return DirectOrderOutcome.ACCEPTED
    return DirectOrderOutcome.REFUSED_BY_NPC


def _action_for(npc: NPC, order: DirectOrder) -> Action:
    if order.action_type == ActionType.MOVE_TO:
        return Action(order.action_type, target=order.target)
    if order.action_type in (ActionType.BUILD, ActionType.PLANT_WHEAT):
        return Action(order.action_type, target=order.target or npc.tile_pos)
    return Action(order.action_type)
