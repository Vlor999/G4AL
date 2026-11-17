"""Interpreted voice orders and how they become NPC actions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from game.actions import Action, ActionType
from game.npc import NPC
from game.settings import ORDER_SPEECH_DURATION_FRAMES, TTS_MAX_SPEAKERS


@dataclass(frozen=True)
class NpcOrder:
    """One order addressed to one NPC.

    ``action_type`` is ``None`` when the order named an action the game does not know:
    the NPC still answers in the log but receives no action.
    """

    npc_id: int
    npc_name: str
    action_type: ActionType | None
    voice_line: str


@dataclass(frozen=True)
class OrderOutcome:
    """What became of one order: whether its NPC took the action, and whether its voice
    line is among the ones to speak aloud (at most ``TTS_MAX_SPEAKERS`` per command)."""

    order: NpcOrder
    is_accepted: bool
    is_spoken: bool


def apply_orders(npcs: Sequence[NPC], orders: Sequence[NpcOrder]) -> list[OrderOutcome]:
    """Enqueue each order's action on its NPC and return one outcome per handled order.

    An order whose NPC id is unknown goes to the first NPC; with no NPC at all, it is
    dropped and has no outcome. Build and plant orders target the NPC's own tile.
    """
    outcomes: list[OrderOutcome] = []
    spoken_count = 0
    for order in orders:
        npc = _find_npc_or_first(npcs, order.npc_id)
        if npc is None:
            continue
        is_accepted = _enqueue_order(npc, order.action_type)
        is_spoken = is_accepted and spoken_count < TTS_MAX_SPEAKERS
        if is_accepted:
            npc.say(order.voice_line, duration_frames=ORDER_SPEECH_DURATION_FRAMES)
        if is_spoken:
            spoken_count += 1
        outcomes.append(OrderOutcome(order, is_accepted=is_accepted, is_spoken=is_spoken))
    return outcomes


def _find_npc_or_first(npcs: Sequence[NPC], npc_id: int) -> NPC | None:
    for npc in npcs:
        if npc.id == npc_id:
            return npc
    return npcs[0] if npcs else None


def _enqueue_order(npc: NPC, action_type: ActionType | None) -> bool:
    if action_type is None:
        return False
    if action_type in (ActionType.BUILD, ActionType.PLANT_WHEAT):
        return npc.enqueue(Action(action_type, target=npc.tile_pos))
    return npc.enqueue(Action(action_type))
