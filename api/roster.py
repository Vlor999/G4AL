"""Single source of truth for every NPC identity.

Each NPC is defined *once* as an ``NPCProfile`` that bundles:
  • **name** – the canonical NPC name (enum).
  • **soul** – a personality blurb fed to the LLM for in-character lines.
  • **voice** – the ElevenLabs preset voice (enum).

All other modules should import derived helpers from here rather than
maintaining their own parallel dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════
#  ElevenLabs voice library
# ═══════════════════════════════════════════════════════════════════════════


class ElevenLabsVoice(Enum):
    """Available ElevenLabs preset voices with their API IDs."""

    # Female voices
    RACHEL = "21m00Tcm4TlvDq8ikWAM"  # calm, mature
    DOMI = "AZnzlk1XvdvUeBnXmlld"  # strong, confident
    BELLA = "EXAVITQu4vr4xnSDxMaL"  # soft, warm
    ELLI = "MF3mGyEYCl7XYWbV9V6O"  # young, cheerful

    # Male voices
    JOSH = "TxGEqnHWrfWFTfGW9XjX"  # deep, authoritative
    ARNOLD = "VR6AewLTigWG4xSOukaG"  # crisp, military
    ADAM = "pNInz6obpgDQGcFmaJgB"  # deep, resonant
    SAM = "yoZ06aMxZJJ28mfd3POQ"  # raspy, older
    ANTONI = "ErXwobaYiN019PkySvjV"  # warm, young male


# ═══════════════════════════════════════════════════════════════════════════
#  NPC Names
# ═══════════════════════════════════════════════════════════════════════════


class NPCName(Enum):
    """All available NPC names."""

    BOB = "Bob"
    PAUL = "Paul"
    THOMAS = "Thomas"
    MARIE = "Marie"
    SAM = "Sam"
    LISA = "Lisa"



@dataclass(frozen=True)
class NPCProfile:
    """Immutable identity card for one NPC."""

    name: NPCName  # canonical NPC name (enum)
    soul: str  # personality description (for LLM prompts)
    voice: ElevenLabsVoice  # ElevenLabs preset voice (enum)


# ═══════════════════════════════════════════════════════════════════════════
#  Master registry – the ONE place to add / edit / remove NPCs
# ═══════════════════════════════════════════════════════════════════════════

NPC_PROFILES: tuple[NPCProfile, ...] = (
    NPCProfile(
        name=NPCName.BOB,
        soul=(
            "Bob keeps complaining about everything. He's grumpy and always finds fault with things."
        ),
        voice=ElevenLabsVoice.RACHEL,
    ),
    NPCProfile(
        name=NPCName.PAUL,
        soul=(
            "Paul is a calm and thoughtful character. He speaks slowly and deliberately, "
            "preferring to think before acting. He's a natural leader who values "
            "teamwork and consensus."
        ),
        voice=ElevenLabsVoice.ARNOLD,
    ),
    NPCProfile(
        name=NPCName.THOMAS,
        soul=(
            "Thomas is a curious and inquisitive character. He asks many questions "
            "and loves to learn new things. He's always eager to explore new ideas "
            "and approaches problems with an open mind."
        ),
        voice=ElevenLabsVoice.SAM,
    ),
    NPCProfile(
        name=NPCName.MARIE,
        soul=(
            "Marie is a sarcastic and witty rogue. She always has a quip ready "
            "and loves to tease others. She complains dramatically but gets "
            "the job done faster than anyone."
        ),
        voice=ElevenLabsVoice.BELLA,
    ),
    NPCProfile(
        name=NPCName.SAM,
        soul=(
            "Sam is a playful and energetic character. He enjoys making jokes and "
            "often lightens the mood with his antics. He's quick on his feet and "
            "enjoys challenges."
        ),
        voice=ElevenLabsVoice.ANTONI,
    ),
    NPCProfile(
        name=NPCName.LISA,
        soul=(
            "Lisa is a focused and determined character. She's highly organized and "
            "takes pride in her work. She's very reliable and gets things done efficiently."
        ),
        voice=ElevenLabsVoice.DOMI,
    ),
        
    
)


# ═══════════════════════════════════════════════════════════════════════════
#  Derived lookups – generated once from NPC_PROFILES
# ═══════════════════════════════════════════════════════════════════════════

NPC_NAMES: list[str] = [p.name.value for p in NPC_PROFILES]
"""Ordered list of all canonical NPC names (as display strings)."""

CHARACTER_SOULS: dict[str, str] = {p.name.value: p.soul for p in NPC_PROFILES}
"""NPC name → personality description (for LLM prompts)."""

NPC_VOICE_MAP: dict[str, str] = {p.name.value: p.voice.value for p in NPC_PROFILES}
"""NPC name → ElevenLabs voice ID."""


def get_soul(name: str) -> str:
    """Return the personality blurb for *name*, with a generic fallback."""
    return CHARACTER_SOULS.get(
        name,
        (
            f"{name} is a dependable worker with a neutral personality. "
            "They follow orders without much fuss and keep to themselves."
        ),
    )
