"""Mistral LLM integration – interprets natural-language commands and returns
structured NPC orders with in-character voice lines.

Uses the Mistral API with JSON-mode to guarantee a parseable response.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

from mistralai import Mistral

from api.characters import get_soul
from api.logger import pipeline_logger


# ═══════════════════════════════════════════════════════════════════════════
#  Data types
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class NPCOrder:
    """Structured output returned by the LLM."""
    npc_name: str           # matched NPC name
    npc_id: int             # NPC numeric id
    action: str             # one of: chop_wood, mine_rock, build, move_to
    voice_line: str         # in-character spoken line


VALID_ACTIONS = ["chop_wood", "mine_rock", "build", "move_to"]


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
MODEL = "mistral-small-latest"


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
orders to NPCs (bots). Your job is to:

1. **Identify which NPC** the player is talking to (match by name, nickname, or context).
2. **Determine the action** from this list: {actions}.
3. **Generate a short voice line** (1-2 sentences max) that the NPC would say in response, \
   staying perfectly in character based on their personality description below.

─── NPC Roster ───
{roster}

─── Character Personalities ───
{personalities}

─── Rules ───
• If the player's intent is ambiguous, pick the most likely action.
• **IMPORTANT: The voice line MUST be in the exact same language as the player's command.** \
  If they write in French, reply in French. If Spanish, reply in Spanish. Always match the input language.
• If the NPC name is misspelled or abbreviated, do your best to match it.
• If you truly cannot determine the NPC, pick the first idle NPC from the roster.
• The voice line MUST reflect the NPC's unique personality.
• Keep voice lines short, punchy, and fun.
• Reply with **only** valid JSON – no markdown, no explanation.

─── Output format (strict JSON) ───
{{
  "npc_name": "<exact NPC name from roster>",
  "npc_id": <integer>,
  "action": "<one of: {actions}>",
  "voice_line": "<in-character line>"
}}
"""


def _build_system_prompt() -> str:
    roster = _build_roster_table()
    personalities = "\n\n".join(
        f"**{info['name']}**: {get_soul(info['name'])}"
        for info in _npc_roster.values()
    )
    return SYSTEM_PROMPT.format(
        actions=", ".join(VALID_ACTIONS),
        roster=roster,
        personalities=personalities or "(no personalities loaded)",
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════

def interpret_command(player_input: str) -> Optional[NPCOrder]:
    """Send a natural-language command to Mistral and return a structured NPCOrder.

    Returns None if parsing fails or the API is unavailable.
    """
    client = _get_client()
    system = _build_system_prompt()

    pipeline_logger.llm_start(input_text=player_input)

    try:
        response = client.chat.complete(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": player_input},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=256,
        )

        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)

        # token usage from the API response
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        # Validate & normalize
        action = data.get("action", "").lower()
        if action not in VALID_ACTIONS:
            action = "chop_wood"  # safe fallback

        npc_name = data.get("npc_name", "")
        npc_id = int(data.get("npc_id", 0))
        voice_line = data.get("voice_line", "...")

        # Cross-check against roster
        roster_entry = _npc_roster.get(npc_name.lower())
        if roster_entry:
            npc_name = roster_entry["name"]
            npc_id = roster_entry["id"]
        elif _npc_roster:
            # LLM returned unknown name – fallback to first NPC
            first = next(iter(_npc_roster.values()))
            npc_name = first["name"]
            npc_id = first["id"]

        order = NPCOrder(
            npc_name=npc_name,
            npc_id=npc_id,
            action=action,
            voice_line=voice_line,
        )

        pipeline_logger.llm_end(
            order=asdict(order),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=MODEL,
        )
        return order

    except Exception as e:
        pipeline_logger.llm_end(order=None, error=str(e))
        print(f"[LLM ERROR] {e}")
        return None
