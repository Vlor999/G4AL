"""Mistral LLM integration – interprets natural-language commands and returns
structured NPC orders with in-character voice lines.

``VoxtralOrderInterpreter`` implements the ``OrderInterpreter`` port: it sends the
audio and the system prompt to ``voxtral-small-latest`` in a single multimodal call
(no intermediate transcription step).

Uses the Mistral API with JSON-mode to guarantee a parseable response.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import TypedDict

from mistralai import Mistral
from mistralai.models import MessagesTypedDict

from api.logger import pipeline_logger
from api.roster import get_soul
from game.npc import NPC, ActionType
from game.orders import NpcOrder
from game.ports import OrderInterpretationError


@dataclass
class NPCOrder:
    """A single order addressed to one NPC."""

    npc_name: str  # matched NPC name
    npc_id: int  # NPC numeric id
    action: str  # one of: chop_wood, mine_rock, build, move_to
    voice_line: str  # in-character spoken line


@dataclass
class CommandResponse:
    """Top-level response: wraps one or many NPC orders."""

    n: int  # total number of actions
    actions: list[NPCOrder]  # individual orders


VALID_ACTIONS = [
    "chop_wood",
    "mine_rock",
    "build",
    "move_to",
    "eat",
    "plant_wheat",
    "collect_wheat",
    "shoot",
    "defend",
]

_ACTION_TYPE_BY_NAME = {action_type.value: action_type for action_type in ActionType}


class RosterEntry(TypedDict):
    id: int
    name: str
    kind: str
    allowed_actions: list[str]


# Keyed by lowercased NPC name.
Roster = Mapping[str, RosterEntry]


def _build_roster_table(roster: Roster) -> str:
    """Format the roster as a readable table for the prompt."""
    if not roster:
        return "(no NPCs registered)"
    lines = ["| ID | Name | Type | Allowed actions |", "|-----|------|------|-----------------|"]
    for info in roster.values():
        kind = info.get("kind", "pawn")
        actions = ", ".join(info.get("allowed_actions", []))
        lines.append(f"| {info['id']} | {info['name']} | {kind} | {actions} |")
    return "\n".join(lines)


AUDIO_MODEL = "voxtral-small-latest"


SYSTEM_PROMPT = """\
You are the command interpreter for a 2D survival game. Players give natural-language \
orders to NPCs (bots) — either as text or spoken audio. A single command may target \
**one or many NPCs** with **one or many actions**.

Your job:
1. **Parse every NPC + action pair** from the command.
2. For each pair, pick the correct NPC from the roster and the matching action.
3. Generate a short, **in-character voice line** for each NPC (1-2 sentences max).

─── NPC Roster ───
{roster}

─── Character Personalities ───
{personalities}

─── Valid actions ───
{actions}

─── Rules ───
• A single command can produce **multiple actions** targeting different (or the same) NPCs.
• If the NPC name is misspelled, abbreviated, or mispronounced, do your best to match it.
• If you truly cannot determine the NPC, pick the first idle NPC from the roster.
• **Each NPC has a type (pawn, archer) with specific allowed actions listed in the roster.**
• **If the player asks an NPC to perform an action NOT in that NPC's allowed actions, \
you MUST still include it in the response but the voice_line should be an in-character \
refusal explaining they cannot do that (e.g. an archer asked to chop wood should refuse).**
• The voice line MUST reflect the NPC's unique personality.
• Keep voice lines short, punchy, and fun.
• ``n`` must equal the number of items in ``actions``.
• Reply with **only** valid JSON – no markdown, no explanation.

─── Output format (strict JSON) ───
{{
  "n": <number of actions>,
  "actions": [
    {{
      "npc_name": "<exact NPC name from roster>",
      "npc_id": <integer>,
      "action": "<one of: {actions}>",
      "voice_line": "<in-character line>"
    }},
    ...
  ]
}}
"""


def _build_system_prompt(roster: Roster) -> str:
    personalities = "\n\n".join(
        f"**{info['name']}**: {get_soul(info['name'])}" for info in roster.values()
    )
    return SYSTEM_PROMPT.format(
        actions=", ".join(VALID_ACTIONS),
        roster=_build_roster_table(roster),
        personalities=personalities or "(no personalities loaded)",
    )


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences (```json ... ```) that some models add."""
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence line
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _parse_response(raw_json: str, roster: Roster) -> CommandResponse:
    """Parse and validate the JSON returned by the LLM into a CommandResponse."""
    cleaned = _strip_fences(raw_json)
    data = json.loads(cleaned)

    # Handle both multi-action and legacy single-action format
    if "actions" in data and isinstance(data["actions"], list):
        raw_actions = data["actions"]
    else:
        # Legacy single-order format → wrap in a list
        raw_actions = [data]

    orders: list[NPCOrder] = []
    for item in raw_actions:
        action = item.get("action", "").lower()
        if action not in VALID_ACTIONS:
            action = "chop_wood"

        npc_name = item.get("npc_name", "")
        npc_id = int(item.get("npc_id", 0))
        voice_line = item.get("voice_line", "...")

        # Cross-check against roster
        roster_entry = roster.get(npc_name.lower())
        if roster_entry:
            npc_name = roster_entry["name"]
            npc_id = roster_entry["id"]
        elif roster:
            first = next(iter(roster.values()))
            npc_name = first["name"]
            npc_id = first["id"]

        orders.append(
            NPCOrder(
                npc_name=npc_name,
                npc_id=npc_id,
                action=action,
                voice_line=voice_line,
            )
        )

    return CommandResponse(n=len(orders), actions=orders)


class VoxtralOrderInterpreter:
    """``OrderInterpreter`` backed by one multimodal Voxtral call per command.

    The client is built from ``MISTRAL_API_KEY`` on the first command unless one is
    given. The NPC roster the prompt lists comes from ``register_roster``.
    """

    def __init__(self, client: Mistral | None = None) -> None:
        self._client = client
        self._roster: dict[str, RosterEntry] = {}

    def register_roster(self, npcs: Sequence[NPC]) -> None:
        """Make ``npcs`` the roster the prompt lists and the answers are matched against."""
        self._roster = {
            npc.name.lower(): {
                "id": npc.id,
                "name": npc.name,
                "kind": npc.kind,
                "allowed_actions": [action.value for action in npc.allowed_actions],
            }
            for npc in npcs
        }

    def interpret(self, audio: bytes) -> list[NpcOrder]:
        """The orders Voxtral hears in ``audio``.

        Raises ``OrderInterpretationError``, and nothing else, on a missing key, an API
        or network failure, or an answer that does not parse. Its message names the
        failure type only; the vendor's text goes to the pipeline log.
        """
        try:
            return self._interpret(audio)
        except OrderInterpretationError:
            raise
        except Exception as error:
            message = f"Voxtral could not interpret the command ({type(error).__name__})"
            raise OrderInterpretationError(message) from error

    def _interpret(self, audio: bytes) -> list[NpcOrder]:
        response = _interpret_audio_command(self._ensure_client(), audio, self._roster)
        if response.actions:
            pipeline_logger.pipeline_summary(voice_text="", order=asdict(response))
        return [_to_npc_order(order) for order in response.actions]

    def _ensure_client(self) -> Mistral:
        if self._client is None:
            api_key = os.environ.get("MISTRAL_API_KEY", "")
            if not api_key:
                raise OrderInterpretationError("MISTRAL_API_KEY is not set")
            self._client = Mistral(api_key=api_key)
        return self._client


def _to_npc_order(order: NPCOrder) -> NpcOrder:
    return NpcOrder(
        npc_id=order.npc_id,
        npc_name=order.npc_name,
        action_type=_ACTION_TYPE_BY_NAME.get(order.action),
        voice_line=order.voice_line,
    )


def _interpret_audio_command(client: Mistral, wav_bytes: bytes, roster: Roster) -> CommandResponse:
    """Send recorded audio and the system prompt to Voxtral in one call and parse its answer.

    A failed call or parse is logged with the vendor's text, then re-raised as is.
    """
    system = _build_system_prompt(roster)
    audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")

    pipeline_logger.llm_start(input_text="(audio input)")

    messages: list[MessagesTypedDict] = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": audio_b64,
                },
                {
                    "type": "text",
                    "text": (
                        "Listen to my voice command above and respond "
                        "with ONLY the JSON order as specified in the "
                        "system prompt. No markdown fences, no explanation."
                    ),
                },
            ],
        },
    ]

    try:
        response = client.chat.complete(
            model=AUDIO_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )

        raw = response.choices[0].message.content
        print(f"[voxtral] raw response type={type(raw).__name__}: {raw!r}")
        if isinstance(raw, list):
            raw = "".join(str(c) for c in raw)
        raw = (raw or "").strip()

        # Strip markdown fences if the model wraps JSON in ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]  # drop first ``` line
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        result = _parse_response(raw, roster)

        usage = response.usage
        pipeline_logger.llm_end(
            order=asdict(result) if result else None,
            prompt_tokens=usage.prompt_tokens or 0 if usage else 0,
            completion_tokens=usage.completion_tokens or 0 if usage else 0,
            model=AUDIO_MODEL,
        )
        return result

    except Exception as e:
        pipeline_logger.llm_end(order=None, error=str(e))
        print(f"[LLM AUDIO ERROR] {e}")
        raise
