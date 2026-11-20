import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

import pytest
from mistralai.client import Mistral

from api.constants import AUDIO_MODEL, ORDERS_TOOL_NAME, TEXT_MODEL
from api.interpreter import MistralOrderInterpreter
from api.logger import PipelineLogger
from api.order_contract import ORDERS_SCHEMA
from game.actions import ActionType
from game.orders import CommandRefused, NpcOrder, RefusalReason
from game.ports import OrderInterpretationError
from tests.conftest import LlmEndRecords, MapBuilder
from tests.test_orders import make_npcs


def tool_call(arguments: dict[str, Any] | str, name: str = ORDERS_TOOL_NAME) -> SimpleNamespace:
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


def answer_with(tool_calls: list[SimpleNamespace] | None, content: str = "") -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)


class FakeChat:
    def __init__(self, answer: SimpleNamespace | Exception) -> None:
        self.answer = answer
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def interpreter_answering(
    answer: SimpleNamespace | Exception, build_map: MapBuilder | None = None
) -> tuple[MistralOrderInterpreter, FakeChat]:
    chat = FakeChat(answer)
    interpreter = MistralOrderInterpreter(
        cast(Mistral, SimpleNamespace(chat=chat)), pipeline_logger=PipelineLogger()
    )
    if build_map is not None:
        interpreter.register_roster(make_npcs(build_map))
    return interpreter, chat


VOICE_ORDER_ACTION_VALUES = [
    "chop_wood",
    "mine_rock",
    "build",
    "eat",
    "plant_wheat",
    "collect_wheat",
    "shoot",
    "defend",
]
"""The actions the model may answer with, written out so a new or renamed ``ActionType``
value fails the drift test until this list, and the prompt, are reviewed."""


def test_schema_actions_are_the_listed_voice_order_actions() -> None:
    action_schema = ORDERS_SCHEMA["properties"]["orders"]["items"]["properties"]["action"]

    assert action_schema["enum"] == VOICE_ORDER_ACTION_VALUES


def test_prompt_roster_lists_no_action_a_voice_order_cannot_give(build_map: MapBuilder) -> None:
    interpreter, chat = interpreter_answering(answer_with([tool_call({"orders": []})]), build_map)

    interpreter.interpret_voice(b"RIFF")

    [call] = chat.calls
    system_prompt = call["messages"][0]["content"]
    assert "chop_wood" in system_prompt
    assert ActionType.MOVE_TO.value not in system_prompt


def interpret_typed(interpreter: MistralOrderInterpreter) -> object:
    return interpreter.interpret_text("Bob, chop wood")


def interpret_spoken(interpreter: MistralOrderInterpreter) -> object:
    return interpreter.interpret_voice(b"RIFF")


@pytest.mark.parametrize(
    ("interpret", "model"),
    [(interpret_typed, TEXT_MODEL), (interpret_spoken, AUDIO_MODEL)],
    ids=["typed", "spoken"],
)
def test_each_input_forces_the_orders_tool_call_on_its_model(
    interpret: Callable[[MistralOrderInterpreter], object], model: str
) -> None:
    interpreter, chat = interpreter_answering(answer_with([tool_call({"orders": []})]))

    interpret(interpreter)

    [call] = chat.calls
    assert call["model"] == model
    assert call["tool_choice"] == "any"
    assert call["parallel_tool_calls"] is False
    assert [tool["function"]["name"] for tool in call["tools"]] == [ORDERS_TOOL_NAME]
    assert call["tools"][0]["function"]["parameters"] is ORDERS_SCHEMA


def test_a_typed_command_is_sent_as_text_after_the_shared_system_prompt(
    build_map: MapBuilder,
) -> None:
    interpreter, chat = interpreter_answering(answer_with([tool_call({"orders": []})]), build_map)

    interpreter.interpret_text("Bob, chop wood")
    interpreter.interpret_voice(b"RIFF")

    typed_call, spoken_call = chat.calls
    assert typed_call["messages"][0] == spoken_call["messages"][0]
    assert typed_call["messages"][1]["content"].endswith("\nBob, chop wood")


@pytest.mark.parametrize("encode", [lambda args: args, json.dumps], ids=["dict", "json-string"])
def test_interpret_maps_each_called_order_to_an_npc_order(
    build_map: MapBuilder, encode: Callable[[dict[str, Any]], Any]
) -> None:
    npcs = make_npcs(build_map)
    pawn, archer = npcs
    arguments = {
        "orders": [
            {"npc_id": pawn.id, "action": "mine_rock", "voice_line": "Fine."},
            {"npc_id": archer.id, "action": "shoot", "voice_line": "Aim!"},
        ]
    }
    interpreter, _ = interpreter_answering(answer_with([tool_call(encode(arguments))]))
    interpreter.register_roster(npcs)

    orders = interpreter.interpret_voice(b"RIFF")

    assert orders == [
        NpcOrder(pawn.id, pawn.name, ActionType.MINE_ROCK, "Fine."),
        NpcOrder(archer.id, archer.name, ActionType.SHOOT, "Aim!"),
    ]


def test_interpret_merges_the_orders_of_every_orders_call(build_map: MapBuilder) -> None:
    npcs = make_npcs(build_map)
    pawn, archer = npcs
    first_call = tool_call(
        {"orders": [{"npc_id": pawn.id, "action": "chop_wood", "voice_line": "On it."}]}
    )
    second_call = tool_call(
        {"orders": [{"npc_id": archer.id, "action": "defend", "voice_line": "Ready."}]}
    )
    interpreter, _ = interpreter_answering(answer_with([first_call, second_call]))
    interpreter.register_roster(npcs)

    orders = interpreter.interpret_voice(b"RIFF")

    assert orders == [
        NpcOrder(pawn.id, pawn.name, ActionType.CHOP_WOOD, "On it."),
        NpcOrder(archer.id, archer.name, ActionType.DEFEND, "Ready."),
    ]


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        (answer_with(None, content="Bob, chop wood!"), RefusalReason.NO_ORDERS_GIVEN),
        (
            SimpleNamespace(choices=[SimpleNamespace(message=None)], usage=None),
            RefusalReason.NO_ORDERS_GIVEN,
        ),
        (answer_with([tool_call({}, name="other_tool")]), RefusalReason.NO_ORDERS_GIVEN),
        (answer_with([tool_call("{not json")]), RefusalReason.MALFORMED_ANSWER),
        (answer_with([tool_call({"npc_id": 1})]), RefusalReason.MALFORMED_ANSWER),
        (answer_with([tool_call({"orders": "chop"})]), RefusalReason.MALFORMED_ANSWER),
        (answer_with([tool_call({"orders": ["chop"]})]), RefusalReason.MALFORMED_ANSWER),
        (
            answer_with(
                [tool_call({"orders": [{"npc_id": "1", "action": "eat", "voice_line": ""}]})]
            ),
            RefusalReason.MALFORMED_ANSWER,
        ),
        (
            answer_with(
                [tool_call({"orders": [{"npc_id": 1, "action": "dance", "voice_line": ""}]})]
            ),
            RefusalReason.UNKNOWN_ACTION,
        ),
        (
            answer_with(
                [tool_call({"orders": [{"npc_id": -1, "action": "eat", "voice_line": ""}]})]
            ),
            RefusalReason.UNKNOWN_NPC,
        ),
        (
            answer_with(
                [tool_call({"orders": [{"npc_id": 1, "action": "move_to", "voice_line": ""}]})]
            ),
            RefusalReason.ACTION_NEEDS_TARGET,
        ),
        (
            answer_with(
                [
                    tool_call({"orders": []}),
                    tool_call({"orders": [{"npc_id": 1, "action": "dance", "voice_line": ""}]}),
                ]
            ),
            RefusalReason.UNKNOWN_ACTION,
        ),
    ],
    ids=[
        "prose-without-call",
        "choice-without-message",
        "other-tool",
        "arguments-not-json",
        "orders-missing",
        "orders-not-a-list",
        "order-not-an-object",
        "npc-id-not-an-integer",
        "unknown-action",
        "unknown-npc",
        "move-to-without-target",
        "second-orders-call-refused",
    ],
)
def test_interpret_refuses_an_answer_that_breaks_the_order_contract(
    build_map: MapBuilder, answer: SimpleNamespace, reason: RefusalReason
) -> None:
    interpreter, _ = interpreter_answering(answer, build_map)

    assert interpreter.interpret_voice(b"RIFF") == CommandRefused(reason)


@pytest.mark.parametrize(
    ("answer", "expected_message"),
    [
        (
            ConnectionError("network down"),
            "Mistral could not interpret the command (ConnectionError)",
        ),
        (
            SimpleNamespace(choices=[], usage=None),
            "Mistral could not interpret the command (IndexError)",
        ),
    ],
    ids=["client-failure", "answer-without-choice"],
)
def test_interpret_raises_only_the_port_error_without_the_vendor_text(
    answer: SimpleNamespace | Exception, expected_message: str
) -> None:
    interpreter, _ = interpreter_answering(answer)

    with pytest.raises(OrderInterpretationError) as raised:
        interpreter.interpret_text("Bob, chop wood")

    assert str(raised.value) == expected_message


@pytest.mark.parametrize(
    ("prompt_audio_seconds", "audio_cost"),
    [(90, 0.006), (None, 0.0)],
    ids=["audio-reported", "audio-not-reported"],
)
def test_the_logged_cost_prices_the_audio_seconds_of_the_answer(
    llm_end_records: LlmEndRecords, prompt_audio_seconds: int | None, audio_cost: float
) -> None:
    usage = SimpleNamespace(
        prompt_tokens=1_000_000, completion_tokens=0, prompt_audio_seconds=prompt_audio_seconds
    )
    answer = answer_with([tool_call({"orders": []})])
    answer.usage = usage
    interpreter, _ = interpreter_answering(answer)

    interpreter.interpret_voice(b"RIFF")

    [(_, extra)] = llm_end_records
    assert extra["audio_cost_usd"] == pytest.approx(audio_cost)
    assert extra["cost_usd"] == pytest.approx(0.1 + audio_cost)
