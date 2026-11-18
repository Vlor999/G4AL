"""Ports of the domain: every ``Protocol`` the game needs from the outside world.

Adapters in ``api/`` implement them; the entry point injects the adapters. A port is
named after a game capability and its methods after game actions, never after a
vendor call. A port whose method can fail to its caller declares the error its
adapters translate vendor failures into.
"""

from __future__ import annotations

from typing import Protocol

from game.orders import CommandRefused, NpcOrder


class OrderInterpretationError(Exception):
    """The interpreter service could not be reached or failed (key, network, API)."""


class OrderInterpreter(Protocol):
    """Turns a spoken command into orders for the NPCs."""

    def interpret(self, audio: bytes) -> list[NpcOrder] | CommandRefused:
        """The orders heard in ``audio`` (a WAV recording); empty when none were.

        Returns ``CommandRefused`` when the service answered but its answer breaks the
        order contract. Raises ``OrderInterpretationError`` when the service fails, and
        nothing else: implementations translate every other exception into it.
        Blocks for the duration of the call: never run it on the game loop thread.
        """
        ...


class VoiceLineSpeaker(Protocol):
    """Says an NPC's voice line aloud.

    ``speak`` only queues the line and returns at once; a line that cannot be voiced
    is dropped and logged by the adapter, so the port has no error of its own.
    """

    def speak(self, voice_line: str, npc_name: str) -> None:
        """Queue ``voice_line`` to be said in ``npc_name``'s voice."""
        ...
