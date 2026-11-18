"""Mistral Voxtral adapter of the ``OrderInterpreter`` port.

``VoxtralOrderInterpreter`` sends the recorded audio and the system prompt to Voxtral in
one multimodal call (no intermediate transcription step). The answer is constrained on
the API side: Voxtral must call the ``give_npc_orders`` function (``tool_choice="any"``),
whose JSON schema lists the actions of ``ActionType``. The call's arguments are then
validated into ``NpcOrder`` values; an answer that breaks the contract becomes a
``CommandRefused`` outcome.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

from loguru import logger
from mistralai import Mistral
from mistralai.models import ChatCompletionResponse, MessagesTypedDict, ToolTypedDict

from api.constants import AUDIO_MODEL, ORDERS_TOOL_NAME
from api.logger import pipeline_logger
from api.roster import get_soul
from game.actions import ActionType
from game.npc import NPC
from game.orders import CommandRefused, NpcOrder, RefusalReason
from game.ports import OrderInterpretationError


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
                        "enum": [action_type.value for action_type in ActionType],
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

ORDERS_TOOL: ToolTypedDict = {
    "type": "function",
    "function": {
        "name": ORDERS_TOOL_NAME,
        "description": "Give the NPCs the orders heard in the player's voice command.",
        "parameters": ORDERS_SCHEMA,
    },
}

SYSTEM_PROMPT = """\
You are the command interpreter for a 2D survival game. Players speak orders to NPCs \
(bots). A single command may target **one or many NPCs** with **one or many actions**.

Your job:
1. Find every NPC + action pair in the command.
2. For each pair, pick the NPC from the roster (its ID) and the matching action.
3. Write a short, **in-character voice line** for each NPC (1-2 sentences max).

─── NPC Roster ───
{roster}

─── Character Personalities ───
{personalities}

─── Rules ───
• Give one order per NPC + action pair, in the order they were spoken.
• If the NPC name is misspelled, abbreviated, or mispronounced, do your best to match it.
• If you truly cannot determine the NPC, give no order for it.
• Each NPC has a type (pawn, archer) with the allowed actions listed in the roster.
• If the player asks an NPC for an action NOT in its allowed actions, still give that \
order, but its voice line is an in-character refusal explaining why it cannot.
• The voice line reflects the NPC's unique personality: short, punchy, and fun.
"""

USER_INSTRUCTION = "Give the orders spoken in this voice command."


def _build_roster_table(roster: Roster) -> str:
    """Format the roster as a readable table for the prompt."""
    if not roster:
        return "(no NPCs registered)"
    lines = ["| ID | Name | Type | Allowed actions |", "|-----|------|------|-----------------|"]
    for info in roster.values():
        actions = ", ".join(info["allowed_actions"])
        lines.append(f"| {info['id']} | {info['name']} | {info['kind']} | {actions} |")
    return "\n".join(lines)


def _build_system_prompt(roster: Roster) -> str:
    personalities = "\n\n".join(
        f"**{info['name']}**: {get_soul(info['name'])}" for info in roster.values()
    )
    return SYSTEM_PROMPT.format(
        roster=_build_roster_table(roster),
        personalities=personalities or "(no personalities loaded)",
    )


def _build_messages(audio: bytes, roster: Roster) -> list[MessagesTypedDict]:
    audio_b64 = base64.b64encode(audio).decode("utf-8")
    return [
        {"role": "system", "content": _build_system_prompt(roster)},
        {
            "role": "user",
            "content": [
                {"type": "input_audio", "input_audio": audio_b64},
                {"type": "text", "text": USER_INSTRUCTION},
            ],
        },
    ]


def read_orders_answer(
    response: ChatCompletionResponse, roster: Roster
) -> list[NpcOrder] | CommandRefused:
    """The orders of Voxtral's ``give_npc_orders`` call, or why the answer is refused."""
    tool_calls = response.choices[0].message.tool_calls or []
    for tool_call in tool_calls:
        if tool_call.function.name == ORDERS_TOOL_NAME:
            return _parse_orders(tool_call.function.arguments, roster)
    return CommandRefused(RefusalReason.NO_ORDERS_GIVEN)


def _parse_orders(
    arguments: dict[str, Any] | str, roster: Roster
) -> list[NpcOrder] | CommandRefused:
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
    npc = roster.get(npc_id)
    if npc is None:
        return CommandRefused(RefusalReason.UNKNOWN_NPC)
    return NpcOrder(
        npc_id=npc_id, npc_name=npc["name"], action_type=action_type, voice_line=voice_line
    )


def _orders_for_log(orders: Sequence[NpcOrder]) -> dict[str, Any]:
    return {
        "orders": [
            {
                "npc_id": order.npc_id,
                "npc_name": order.npc_name,
                "action": order.action_type.value,
                "voice_line": order.voice_line,
            }
            for order in orders
        ]
    }


def _log_answer(response: ChatCompletionResponse, answer: list[NpcOrder] | CommandRefused) -> None:
    usage = response.usage
    prompt_tokens = (usage.prompt_tokens or 0) if usage else 0
    completion_tokens = (usage.completion_tokens or 0) if usage else 0
    if isinstance(answer, CommandRefused):
        pipeline_logger.llm_end(
            order=None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=AUDIO_MODEL,
            error=f"answer refused: {answer.reason}",
        )
        return
    order = _orders_for_log(answer)
    pipeline_logger.llm_end(
        order=order,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model=AUDIO_MODEL,
    )
    if answer:
        pipeline_logger.pipeline_summary(voice_text="", order=order)


class VoxtralOrderInterpreter:
    """``OrderInterpreter`` backed by one multimodal Voxtral call per command.

    The client is built from ``MISTRAL_API_KEY`` on the first command unless one is
    given. The NPC roster the prompt lists comes from ``register_roster``.
    """

    def __init__(self, client: Mistral | None = None) -> None:
        self._client = client
        self._roster: dict[int, RosterEntry] = {}

    def register_roster(self, npcs: Sequence[NPC]) -> None:
        """Make ``npcs`` the roster the prompt lists and the answers are matched against."""
        self._roster = {
            npc.id: {
                "id": npc.id,
                "name": npc.name,
                "kind": npc.kind,
                "allowed_actions": [action.value for action in npc.allowed_actions],
            }
            for npc in npcs
        }

    def interpret(self, audio: bytes) -> list[NpcOrder] | CommandRefused:
        """The orders Voxtral hears in ``audio``, or ``CommandRefused`` for an answer
        that breaks the order contract.

        Raises ``OrderInterpretationError``, and nothing else, on a missing key or any
        other failure (API, network, unexpected answer shape). Its message names the
        failure type only; the failure's type and text go to the log.
        """
        try:
            return self._interpret(audio)
        except OrderInterpretationError:
            raise
        except Exception as error:
            failure = type(error).__name__
            logger.bind(event="order_interpretation", failure=failure).error(
                f"Voxtral interpretation failed: {failure}: {error}"
            )
            message = f"Voxtral could not interpret the command ({failure})"
            raise OrderInterpretationError(message) from error

    def _interpret(self, audio: bytes) -> list[NpcOrder] | CommandRefused:
        client = self._ensure_client()
        pipeline_logger.llm_start(input_text="(audio input)")
        try:
            response = client.chat.complete(
                model=AUDIO_MODEL,
                messages=_build_messages(audio, self._roster),
                tools=[ORDERS_TOOL],
                tool_choice="any",
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as error:
            pipeline_logger.llm_end(order=None, error=str(error))
            raise
        answer = read_orders_answer(response, self._roster)
        _log_answer(response, answer)
        return answer

    def _ensure_client(self) -> Mistral:
        if self._client is None:
            api_key = os.environ.get("MISTRAL_API_KEY", "")
            if not api_key:
                raise OrderInterpretationError("MISTRAL_API_KEY is not set")
            self._client = Mistral(api_key=api_key)
        return self._client
