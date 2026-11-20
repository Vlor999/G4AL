"""The order contract every LLM provider shares: roster, system prompt, answer schema
and the validation of an answer into ``NpcOrder`` values.

Provider-neutral: no vendor SDK here. An adapter sends ``build_system_prompt`` and
``ORDERS_SCHEMA`` in its vendor's request shape and hands the arguments of the answer
to ``parse_orders``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from api.logger import LoggedOrder
from api.roster import get_soul
from game.actions import ActionType
from game.npc import NPC
from game.orders import VOICE_ORDER_ACTIONS, CommandRefused, NpcOrder, RefusalReason


class RosterEntry(TypedDict):
    id: int
    name: str
    kind: str
    allowed_actions: list[str]


# Keyed by NPC id.
Roster = Mapping[int, RosterEntry]

ORDERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "orders": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "npc_id": {"type": "integer", "description": "ID of the NPC in the roster"},
                    "action": {
                        "type": "string",
                        "enum": [action_type.value for action_type in VOICE_ORDER_ACTIONS],
                    },
                    "voice_line": {
                        "type": "string",
                        "description": "What the NPC answers, in character, 1-2 sentences",
                    },
                },
                "required": ["npc_id", "action", "voice_line"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["orders"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
You are the command interpreter for a 2D survival game. Players give orders to NPCs \
(bots), by voice or typed. A single command may target **one or many NPCs** with \
**one or many actions**.

Your job:
1. Find every NPC + action pair in the command.
2. For each pair, pick the NPC from the roster (its ID) and the matching action.
3. Write a short, **in-character voice line** for each NPC (1-2 sentences max).

─── NPC Roster ───
{roster}

─── Character Personalities ───
{personalities}

─── Rules ───
• Give one order per NPC + action pair, in the order they were given.
• If the NPC name is misspelled, abbreviated, or mispronounced, do your best to match it.
• If you truly cannot determine the NPC, give no order for it.
• Each NPC has a type (pawn, archer) with the allowed actions listed in the roster.
• If the player asks an NPC for an action NOT in its allowed actions, still give that \
order, but its voice line is an in-character refusal explaining why it cannot.
• The voice line reflects the NPC's unique personality: short, punchy, and fun.
"""


def build_roster(npcs: Sequence[NPC]) -> dict[int, RosterEntry]:
    """The roster of ``npcs``, each NPC's allowed actions narrowed to the ones an order
    without a target tile can give."""
    return {
        npc.id: {
            "id": npc.id,
            "name": npc.name,
            "kind": npc.kind,
            "allowed_actions": [
                action.value for action in npc.allowed_actions if action in VOICE_ORDER_ACTIONS
            ],
        }
        for npc in npcs
    }


def _build_roster_table(roster: Roster) -> str:
    if not roster:
        return "(no NPCs registered)"
    lines = ["| ID | Name | Type | Allowed actions |", "|-----|------|------|-----------------|"]
    for info in roster.values():
        actions = ", ".join(info["allowed_actions"])
        lines.append(f"| {info['id']} | {info['name']} | {info['kind']} | {actions} |")
    return "\n".join(lines)


def build_system_prompt(roster: Roster) -> str:
    personalities = "\n\n".join(
        f"**{info['name']}**: {get_soul(info['name'])}" for info in roster.values()
    )
    return SYSTEM_PROMPT.format(
        roster=_build_roster_table(roster),
        personalities=personalities or "(no personalities loaded)",
    )


def parse_orders(
    arguments: dict[str, Any] | str, roster: Roster
) -> list[NpcOrder] | CommandRefused:
    """The orders of one answer that follows ``ORDERS_SCHEMA`` (a JSON string or its
    decoded object), or why the answer is refused. One bad order refuses them all."""
    try:
        payload = json.loads(arguments) if isinstance(arguments, str) else arguments
        items = payload["orders"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return CommandRefused(RefusalReason.MALFORMED_ANSWER)
    if not isinstance(items, list):
        return CommandRefused(RefusalReason.MALFORMED_ANSWER)
    orders: list[NpcOrder] = []
    for item in items:
        order = _parse_order(item, roster)
        if isinstance(order, CommandRefused):
            return order
        orders.append(order)
    return orders


def _parse_order(item: object, roster: Roster) -> NpcOrder | CommandRefused:
    if not isinstance(item, dict):
        return CommandRefused(RefusalReason.MALFORMED_ANSWER)
    npc_id, action, voice_line = item.get("npc_id"), item.get("action"), item.get("voice_line")
    if not isinstance(npc_id, int) or not isinstance(voice_line, str):
        return CommandRefused(RefusalReason.MALFORMED_ANSWER)
    try:
        action_type = ActionType(action)
    except ValueError:
        return CommandRefused(RefusalReason.UNKNOWN_ACTION)
    if action_type not in VOICE_ORDER_ACTIONS:
        return CommandRefused(RefusalReason.ACTION_NEEDS_TARGET)
    npc = roster.get(npc_id)
    if npc is None:
        return CommandRefused(RefusalReason.UNKNOWN_NPC)
    return NpcOrder(
        npc_id=npc_id, npc_name=npc["name"], action_type=action_type, voice_line=voice_line
    )


def build_orders_for_log(orders: Sequence[NpcOrder]) -> dict[str, list[LoggedOrder]]:
    logged_orders = [
        LoggedOrder(
            npc_id=order.npc_id,
            npc_name=order.npc_name,
            action=order.action_type.value,
            voice_line=order.voice_line,
        )
        for order in orders
    ]
    return {"orders": logged_orders}
