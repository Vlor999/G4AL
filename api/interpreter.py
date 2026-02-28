"""Mistral LLM integration – interprets natural-language commands and returns
structured NPC orders with in-character voice lines.

Supports two input modes:
  • **Text** – ``interpret_command(text)`` uses ``mistral-small-latest``.
  • **Audio** – ``interpret_audio_command(wav_bytes)`` sends audio + system
    prompt to ``voxtral-mini-latest`` in a single multimodal call (no
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
TEXT_MODEL = "mistral-small-latest"
AUDIO_MODEL = "voxtral-mini-latest"


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
orders to NPCs (bots) — either as text or spoken audio. Your job is to:

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
  If they speak or write in French, reply in French. If Spanish, reply in Spanish. Always match the input language.
• If the NPC name is misspelled, abbreviated, or mispronounced, do your best to match it.
• If you truly cannot determine the NPC, pick the first idle NPC from the roster.
• The voice line MUST reflect the NPC's unique personality.
• Keep voice lines short, punchy, and fun.
• Reply with **only** valid JSON – no markdown, no explanation.

─── Output format (strict JSON) ───
{{{{
  "npc_name": "<exact NPC name from roster>",
  "npc_id": <integer>,
  "action": "<one of: {actions}>",
  "voice_line": "<in-character line>"
}}}}
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
#  Shared response parser
# ═══════════════════════════════════════════════════════════════════════════

def _parse_order(raw_json: str) -> NPCOrder:
    """Parse and validate the JSON returned by the LLM into an NPCOrder."""
    data = json.loads(raw_json)

    # Validate & normalize action
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
        first = next(iter(_npc_roster.values()))
        npc_name = first["name"]
        npc_id = first["id"]

    return NPCOrder(
        npc_name=npc_name,
        npc_id=npc_id,
        action=action,
        voice_line=voice_line,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Public API — text input
# ═══════════════════════════════════════════════════════════════════════════

def interpret_command(player_input: str) -> Optional[NPCOrder]:
    """Send a text command to Mistral and return a structured NPCOrder.

    Returns None if parsing fails or the API is unavailable.
    """
    client = _get_client()
    system = _build_system_prompt()

    pipeline_logger.llm_start(input_text=player_input)

    try:
        response = client.chat.complete(
            model=TEXT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": player_input},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=256,
        )

        raw = response.choices[0].message.content
        if isinstance(raw, list):
            raw = "".join(str(c) for c in raw)
        raw = (raw or "").strip()

        order = _parse_order(raw)

        usage = response.usage
        pipeline_logger.llm_end(
            order=asdict(order),
            prompt_tokens=usage.prompt_tokens or 0 if usage else 0,
            completion_tokens=usage.completion_tokens or 0 if usage else 0,
            model=TEXT_MODEL,
        )
        return order

    except Exception as e:
        pipeline_logger.llm_end(order=None, error=str(e))
        print(f"[LLM ERROR] {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  Public API — audio input  (single multimodal Voxtral call)
# ═══════════════════════════════════════════════════════════════════════════

def interpret_audio_command(wav_bytes: bytes) -> Optional[NPCOrder]:
    """Send recorded audio directly to Voxtral and return a structured NPCOrder.

    This merges transcription + interpretation into one API round-trip.
    The Voxtral model natively understands audio and follows the system
    prompt to output the JSON order.

    Args:
        wav_bytes: WAV-encoded audio bytes from the microphone.

    Returns:
        NPCOrder or None on failure.
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
            max_tokens=256,
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

        order = _parse_order(raw)

        usage = response.usage
        pipeline_logger.llm_end(
            order=asdict(order),
            prompt_tokens=usage.prompt_tokens or 0 if usage else 0,
            completion_tokens=usage.completion_tokens or 0 if usage else 0,
            model=AUDIO_MODEL,
        )
        return order

    except Exception as e:
        pipeline_logger.llm_end(order=None, error=str(e))
        print(f"[LLM AUDIO ERROR] {e}")
        return None
