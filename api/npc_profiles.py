"""The profile of each named NPC: personality for the LLM prompt, ElevenLabs voice.

A profile is keyed by an ``NPCName`` member of ``game/world/npc_names.py``, so adding
an NPC takes a member there and a profile in ``NPC_PROFILES``. A name without a
profile, such as an archer's or a wild archer's, gets the generic soul of
``get_soul`` and the default voice of ``api.tts``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from game.world.npc_names import NPCName


class ElevenLabsVoice(Enum):
    """ElevenLabs preset voices, valued by their API ids."""

    # Female voices
    RACHEL = "21m00Tcm4TlvDq8ikWAM"  # calm, mature
    DOMI = "AZnzlk1XvdvUeBnXmlld"  # strong, confident
    BELLA = "EXAVITQu4vr4xnSDxMaL"  # soft, warm

    # Male voices
    JOSH = "TxGEqnHWrfWFTfGW9XjX"  # deep, authoritative
    ARNOLD = "VR6AewLTigWG4xSOukaG"  # crisp, military
    SAM = "yoZ06aMxZJJ28mfd3POQ"  # raspy, older
    ANTONI = "ErXwobaYiN019PkySvjV"  # warm, young male


@dataclass(frozen=True)
class NPCProfile:
    name: NPCName
    soul: str  # personality description written into the LLM prompt
    voice: ElevenLabsVoice


NPC_PROFILES: tuple[NPCProfile, ...] = (
    NPCProfile(
        name=NPCName.BOB,
        soul=(
            "Bob keeps complaining about everything. He's grumpy and always finds fault with things."
        ),
        voice=ElevenLabsVoice.JOSH,
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


CHARACTER_SOULS: dict[str, str] = {profile.name.value: profile.soul for profile in NPC_PROFILES}

NPC_VOICE_MAP: dict[str, str] = {
    profile.name.value: profile.voice.value for profile in NPC_PROFILES
}


def get_soul(name: str) -> str:
    """Return the personality blurb for *name*, with a generic fallback."""
    return CHARACTER_SOULS.get(
        name,
        (
            f"{name} is a dependable worker with a neutral personality. "
            "They follow orders without much fuss and keep to themselves."
        ),
    )
