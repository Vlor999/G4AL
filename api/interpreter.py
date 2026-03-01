"""Mistral LLM integration – interprets natural-language commands and returns
structured NPC orders with in-character voice lines.

Supports two input modes:
  • **Audio** – ``interpret_audio_command(wav_bytes)`` sends audio + system
    prompt to ``voxtral-small-latest`` in a single multimodal call (no
    intermediate transcription step).

Uses the Mistral API with JSON-mode to guarantee a parseable response.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

from mistralai import Mistral

from api.roster import get_soul
from api.logger import pipeline_logger


# ═══════════════════════════════════════════════════════════════════════════
#  Data types
# ═══════════════════════════════════════════════════════════════════════════


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


VALID_ACTIONS = ["chop_wood", "mine_rock", "build", "move_to", "eat", "plant_wheat", "collect_wheat"]


# ═══════════════════════════════════════════════════════════════════════════
#  NPC roster (set by the game at runtime)
# ═══════════════════════════════════════════════════════════════════════════

# Maps lowercased NPC name → {id, name}
_npc_roster: dict[str, dict] = {}


def register_npcs(npcs: list[dict]) -> None:
    """Called by the game to sync the live NPC list.

    Args:
        npcs: list of {"id": int, "name": str}
    """
    _npc_roster.clear()
    for npc in npcs:
        _npc_roster[npc["name"].lower()] = npc


def _build_roster_table() -> str:
    """Format the roster as a readable table for the prompt."""
    if not _npc_roster:
        return "(no NPCs registered)"
    lines = ["| ID | Name |", "|-----|------|"]
    for info in _npc_roster.values():
        lines.append(f"| {info['id']} | {info['name']} |")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  Mistral client
# ═══════════════════════════════════════════════════════════════════════════

_client: Mistral | None = None
AUDIO_MODEL = "voxtral-small-latest"


def _get_client() -> Mistral:
    global _client
    if _client is None:
        api_key = os.environ.get("MISTRAL_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY not set. Add it to your .env or environment."
            )
        _client = Mistral(api_key=api_key)
    return _client


# ═══════════════════════════════════════════════════════════════════════════
#  System prompt
# ═══════════════════════════════════════════════════════════════════════════

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


def _build_system_prompt() -> str:
    roster = _build_roster_table()
    personalities = "\n\n".join(
        f"**{info['name']}**: {get_soul(info['name'])}" for info in _npc_roster.values()
    )
    return SYSTEM_PROMPT.format(
        actions=", ".join(VALID_ACTIONS),
        roster=roster,
        personalities=personalities or "(no personalities loaded)",
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Shared response parser
# ═══════════════════════════════════════════════════════════════════════════


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences (```json ... ```) that some models add."""
    text = raw.strip()
    if text.startswith("```"):
        # Remove opening fence line
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _parse_response(raw_json: str) -> CommandResponse:
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
        roster_entry = _npc_roster.get(npc_name.lower())
        if roster_entry:
            npc_name = roster_entry["name"]
            npc_id = roster_entry["id"]
        elif _npc_roster:
            first = next(iter(_npc_roster.values()))
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


# ═══════════════════════════════════════════════════════════════════════════
#  Public API — audio input  (single multimodal Voxtral call)
# ═══════════════════════════════════════════════════════════════════════════


def interpret_audio_command(wav_bytes: bytes) -> Optional[CommandResponse]:
    """Send recorded audio directly to Voxtral and return a structured CommandResponse.

    This merges transcription + interpretation into one API round-trip.
    The Voxtral model natively understands audio and follows the system
    prompt to output the JSON order.

    Args:
        wav_bytes: WAV-encoded audio bytes from the microphone.

    Returns:
        CommandResponse or None on failure.
    """
    client = _get_client()
    system = _build_system_prompt()
    audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")

    pipeline_logger.llm_start(input_text="(audio input)")

    try:
        response = client.chat.complete(
            model=AUDIO_MODEL,
            messages=[
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
            ],
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

        result = _parse_response(raw)

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
        return None
