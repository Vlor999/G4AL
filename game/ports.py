"""Ports of the domain: every ``Protocol`` the game needs from the outside world.

Adapters in ``api/`` implement them; the entry point injects the adapters. A port is
named after a game capability and its methods after game actions, never after a
vendor call. A port whose method can fail to its caller declares the error its
adapters translate vendor failures into.
"""

from __future__ import annotations

from typing import Protocol

from game.orders.orders import CommandRefused, NpcOrder


class OrderInterpretationError(Exception):
    """The interpreter service could not be reached or failed (key, network, API)."""


class TextOrderInterpreter(Protocol):
    """Turns a typed command into orders for the NPCs. Every LLM provider implements it."""

    def interpret_text(self, command: str, *, model_id: str) -> list[NpcOrder] | CommandRefused:
        """The orders ``model_id`` finds in ``command``; empty when none were.

        ``model_id`` is the id of one of this provider's models in the model catalog.

        Returns ``CommandRefused`` when the service answered but its answer breaks the
        order contract. Raises ``OrderInterpretationError`` when the service fails, and
        nothing else: implementations translate every other exception into it.
        Blocks for the duration of the call: never run it on the game loop thread.
        """
        ...


class VoiceOrderInterpreter(Protocol):
    """Turns a spoken command into orders for the NPCs.

    ``interpret_voice`` returns the orders ``model_id`` hears in ``audio`` (a WAV
    recording), with the arguments, outcomes, errors and blocking of
    ``TextOrderInterpreter.interpret_text``. Only a provider with speech input
    implements it, and only its voice models are passed; without one, the game takes
    typed commands only.
    """

    def interpret_voice(
        self, audio: bytes, *, model_id: str
    ) -> list[NpcOrder] | CommandRefused: ...


class VoiceLineSpeaker(Protocol):
    """Says an NPC's voice line aloud.

    ``speak`` only queues the line and returns at once; a line that cannot be voiced
    is dropped and logged by the adapter, so the port has no error of its own.
    """

    def speak(self, voice_line: str, npc_name: str) -> None:
        """Queue ``voice_line`` to be said in ``npc_name``'s voice."""
        ...
