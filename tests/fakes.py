"""Fakes of the ports in game/ports.py."""

from game.orders import CommandRefused, NpcOrder
from game.ports import OrderInterpretationError


class ScriptedOrderInterpreter:
    """Answers every command with the same orders, or with `refusal` or `error` when given."""

    def __init__(
        self,
        orders: list[NpcOrder] | None = None,
        refusal: CommandRefused | None = None,
        error: OrderInterpretationError | None = None,
    ) -> None:
        self.orders = orders or []
        self.refusal = refusal
        self.error = error

    def interpret(self, audio: bytes) -> list[NpcOrder] | CommandRefused:
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
