import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

import pytest
from mistralai import Mistral

from api.constants import ORDERS_TOOL_NAME
from api.interpreter import ORDERS_SCHEMA, VoxtralOrderInterpreter
from game.actions import ActionType
from game.orders import VOICE_ORDER_ACTIONS, CommandRefused, NpcOrder, RefusalReason
from game.ports import OrderInterpretationError
from tests.conftest import MapBuilder
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
) -> tuple[VoxtralOrderInterpreter, FakeChat]:
    chat = FakeChat(answer)
    interpreter = VoxtralOrderInterpreter(cast(Mistral, SimpleNamespace(chat=chat)))
    if build_map is not None:
        interpreter.register_roster(make_npcs(build_map))
    return interpreter, chat


def test_schema_actions_are_the_voice_order_actions() -> None:
    action_schema = ORDERS_SCHEMA["properties"]["orders"]["items"]["properties"]["action"]

    assert action_schema["enum"] == [action_type.value for action_type in VOICE_ORDER_ACTIONS]
    assert ActionType.MOVE_TO.value not in action_schema["enum"]


def test_prompt_roster_lists_no_action_a_voice_order_cannot_give(build_map: MapBuilder) -> None:
    interpreter, chat = interpreter_answering(answer_with([tool_call({"orders": []})]), build_map)

    interpreter.interpret(b"RIFF")

    [call] = chat.calls
    system_prompt = call["messages"][0]["content"]
    assert "chop_wood" in system_prompt
    assert ActionType.MOVE_TO.value not in system_prompt


def test_interpret_forces_the_orders_tool_call() -> None:
    interpreter, chat = interpreter_answering(answer_with([tool_call({"orders": []})]))

    interpreter.interpret(b"RIFF")

    [call] = chat.calls
    assert call["tool_choice"] == "any"
    assert call["parallel_tool_calls"] is False
    assert [tool["function"]["name"] for tool in call["tools"]] == [ORDERS_TOOL_NAME]
    assert call["tools"][0]["function"]["parameters"] is ORDERS_SCHEMA


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

    orders = interpreter.interpret(b"RIFF")

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

    orders = interpreter.interpret(b"RIFF")

    assert orders == [
        NpcOrder(pawn.id, pawn.name, ActionType.CHOP_WOOD, "On it."),
        NpcOrder(archer.id, archer.name, ActionType.DEFEND, "Ready."),
    ]


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        (answer_with(None, content="Bob, chop wood!"), RefusalReason.NO_ORDERS_GIVEN),
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

    assert interpreter.interpret(b"RIFF") == CommandRefused(reason)


@pytest.mark.parametrize(
    ("build_interpreter", "expected_message"),
    [
        (
            lambda: interpreter_answering(ConnectionError("network down"))[0],
            "Voxtral could not interpret the command (ConnectionError)",
        ),
        (
            lambda: interpreter_answering(SimpleNamespace(choices=[], usage=None))[0],
            "Voxtral could not interpret the command (IndexError)",
        ),
        (VoxtralOrderInterpreter, "MISTRAL_API_KEY is not set"),
    ],
    ids=["client-failure", "answer-without-choice", "missing-api-key"],
)
def test_interpret_raises_only_the_port_error_without_the_vendor_text(
    build_interpreter: Callable[[], VoxtralOrderInterpreter],
    expected_message: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    with pytest.raises(OrderInterpretationError) as raised:
        build_interpreter().interpret(b"RIFF")

    assert str(raised.value) == expected_message
