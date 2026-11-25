"""What the chat panel shows: the player's commands and the NPCs' voice lines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TypedCommand:
    text: str


@dataclass(frozen=True)
class SpokenCommand:
    """A push-to-talk command: the interpreter hears the audio, so there is no text."""


@dataclass(frozen=True)
class NpcVoiceLine:
    npc_name: str
    voice_line: str


PlayerCommand = TypedCommand | SpokenCommand
ChatMessage = TypedCommand | SpokenCommand | NpcVoiceLine
