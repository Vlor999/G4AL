"""Fakes of the ports in game/ports.py."""

from collections.abc import Callable

from game.orders import CommandRefused, NpcOrder
from game.ports import OrderInterpretationError


class ScriptedOrderInterpreter:
    """Answers every command, typed or spoken, with the same orders, or with `refusal`
    or `error` when given; keeps the commands it received in `commands`."""

    def __init__(
        self,
        orders: list[NpcOrder] | None = None,
        refusal: CommandRefused | None = None,
        error: OrderInterpretationError | None = None,
    ) -> None:
        self.orders = orders or []
        self.refusal = refusal
        self.error = error
        self.commands: list[str | bytes] = []

    def interpret_text(self, command: str) -> list[NpcOrder] | CommandRefused:
        return self._answer(command)

    def interpret_voice(self, audio: bytes) -> list[NpcOrder] | CommandRefused:
        return self._answer(audio)

    def _answer(self, command: str | bytes) -> list[NpcOrder] | CommandRefused:
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        if self.refusal is not None:
            return self.refusal
        return list(self.orders)


class RecordingSpeaker:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str]] = []

    def speak(self, voice_line: str, npc_name: str) -> None:
        self.lines.append((voice_line, npc_name))


def run_now(work: Callable[[], None]) -> None:
    """Runs the engine's background work on the calling thread, so a test sees its result."""
    work()
