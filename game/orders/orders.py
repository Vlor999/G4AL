"""Interpreted voice orders and how they become NPC actions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from game.npcs.actions import ActionType, create_order_action
from game.npcs.npc import NPC
from game.settings import ORDER_SPEECH_DURATION_FRAMES, TTS_MAX_SPEAKERS

VOICE_ORDER_ACTIONS: tuple[ActionType, ...] = tuple(
    action_type for action_type in ActionType if action_type is not ActionType.MOVE_TO
)
"""Actions a spoken order can give. ``move_to`` needs a target tile, which a voice
order does not carry: the player gives it with a right-click instead."""


@dataclass(frozen=True)
class NpcOrder:
    """One spoken order addressed to one NPC.

    Its action is one of ``VOICE_ORDER_ACTIONS``: building it with another one raises
    ``ValueError``, as a domain invariant. The parser in ``api/interpreter.py`` refuses
    such an answer with ``RefusalReason.ACTION_NEEDS_TARGET`` before any ``NpcOrder``
    is built.
    """

    npc_id: int
    npc_name: str
    action_type: ActionType
    voice_line: str

    def __post_init__(self) -> None:
        if self.action_type not in VOICE_ORDER_ACTIONS:
            raise ValueError(f"{self.action_type.value} needs a target tile")


class RefusalReason(StrEnum):
    """Why the answer to a spoken command was refused instead of turned into orders."""

    NO_ORDERS_GIVEN = "no orders given"
    MALFORMED_ANSWER = "malformed answer"
    UNKNOWN_ACTION = "unknown action"
    UNKNOWN_NPC = "unknown npc"
    ACTION_NEEDS_TARGET = "action needs a target tile"


@dataclass(frozen=True)
class CommandRefused:
    """The answer to a spoken command broke the order contract: no order is applied."""

    reason: RefusalReason


@dataclass(frozen=True)
class OrderOutcome:
    """What became of one order: whether its NPC took the action, and whether its voice
    line is among the ones to speak aloud (at most ``TTS_MAX_SPEAKERS`` per command)."""

    order: NpcOrder
    is_accepted: bool
    is_spoken: bool


def apply_orders(npcs: Sequence[NPC], orders: Sequence[NpcOrder]) -> list[OrderOutcome]:
    """Enqueue each order's action on its NPC and return one outcome per order.

    An order whose NPC id is unknown (an NPC that died since the roster was built) is
    not accepted: nothing is enqueued or spoken. Build and plant orders target the
    NPC's own tile.
    """
    npcs_by_id = {npc.id: npc for npc in npcs}
    outcomes: list[OrderOutcome] = []
    spoken_count = 0
    for order in orders:
        npc = npcs_by_id.get(order.npc_id)
        is_accepted = npc is not None and npc.enqueue(
            create_order_action(order.action_type, target=None, own_tile=npc.tile_pos)
        )
        is_spoken = is_accepted and spoken_count < TTS_MAX_SPEAKERS
        if npc is not None and is_accepted:
            npc.say(order.voice_line, duration_frames=ORDER_SPEECH_DURATION_FRAMES)
        if is_spoken:
            spoken_count += 1
        outcomes.append(OrderOutcome(order, is_accepted=is_accepted, is_spoken=is_spoken))
    return outcomes
