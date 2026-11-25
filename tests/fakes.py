"""Fakes of the ports in game/ports.py."""

from collections.abc import Callable, Sequence

from api.model_catalog import MODELS_BY_ID, CatalogModel, LlmProvider
from game.orders.orders import CommandRefused, NpcOrder
from game.ports import OrderInterpretationError
from server.model_selection import ModelSelection, OrderInterpreters

VOICE_MODEL = MODELS_BY_ID["voxtral-small-latest"]
TEXT_MODEL = MODELS_BY_ID["mistral-small-latest"]


class ScriptedOrderInterpreter:
    """Answers every command, typed or spoken, with the same orders, or with `refusal`
    or `error` when given; keeps the commands it received in `commands` and the model
    each one was sent to in `model_ids`."""

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
        self.model_ids: list[str] = []

    def interpret_text(self, command: str, *, model_id: str) -> list[NpcOrder] | CommandRefused:
        return self._answer(command, model_id)

    def interpret_voice(self, audio: bytes, *, model_id: str) -> list[NpcOrder] | CommandRefused:
        return self._answer(audio, model_id)

    def _answer(self, command: str | bytes, model_id: str) -> list[NpcOrder] | CommandRefused:
        self.commands.append(command)
        self.model_ids.append(model_id)
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


def build_model_selection(
    interpreter: ScriptedOrderInterpreter,
    *,
    selected: CatalogModel = VOICE_MODEL,
    available_models: Sequence[CatalogModel] = (VOICE_MODEL, TEXT_MODEL),
    has_voice_adapter: bool = True,
) -> ModelSelection:
    """Mistral models answered by ``interpreter``, as the entry point builds them."""
    interpreters = OrderInterpreters(
        text=interpreter,
        voice=interpreter if has_voice_adapter else None,
        register_roster=lambda npcs: None,
    )
    return ModelSelection(
        available_models=available_models,
        selected=selected,
        interpreters={LlmProvider.MISTRAL: interpreters},
    )


def run_now(work: Callable[[], None]) -> None:
    """Runs the engine's background work on the calling thread, so a test sees its result."""
    work()
