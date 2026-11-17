import json
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

import pytest
from mistralai import Mistral

from api.interpreter import (
    CommandResponse,
    NPCOrder,
    Roster,
    VoxtralOrderInterpreter,
    _parse_response,
)
from game.actions import ActionType
from game.orders import NpcOrder
from game.ports import OrderInterpretationError

ROSTER: Roster = {
    "bob": {"id": 1, "name": "Bob", "kind": "pawn", "allowed_actions": ["chop_wood"]},
    "robin": {"id": 2, "name": "Robin", "kind": "archer", "allowed_actions": ["shoot"]},
}


def test_parse_response_reads_every_action() -> None:
    raw = json.dumps(
        {
            "n": 2,
            "actions": [
                {"npc_name": "bob", "npc_id": 9, "action": "MINE_ROCK", "voice_line": "Fine."},
                {"npc_name": "Robin", "npc_id": 2, "action": "shoot", "voice_line": "Aim!"},
            ],
        }
    )
    assert _parse_response(raw, ROSTER) == CommandResponse(
        n=2,
        actions=[
            NPCOrder(npc_name="Bob", npc_id=1, action="mine_rock", voice_line="Fine."),
            NPCOrder(npc_name="Robin", npc_id=2, action="shoot", voice_line="Aim!"),
        ],
    )


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        (
            {"npc_name": "Bob", "action": "dance", "voice_line": "No."},
            NPCOrder(npc_name="Bob", npc_id=1, action="chop_wood", voice_line="No."),
        ),
        (
            {"npc_name": "Nobody", "action": "eat"},
            NPCOrder(npc_name="Bob", npc_id=1, action="eat", voice_line="..."),
        ),
    ],
    ids=["invalid-action-falls-back-to-chop-wood", "unknown-npc-falls-back-to-first"],
)
def test_parse_response_falls_back(item: dict[str, str], expected: NPCOrder) -> None:
    assert _parse_response(json.dumps(item), ROSTER).actions == [expected]


def test_parse_response_strips_markdown_fences() -> None:
    raw = '```json\n{"npc_name": "Robin", "action": "defend", "voice_line": "On guard."}\n```'
    assert _parse_response(raw, ROSTER).actions[0].action == "defend"


def test_parse_response_rejects_malformed_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_response("{not json", ROSTER)


class FakeChat:
    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer

    def complete(self, **_: Any) -> SimpleNamespace:
        if isinstance(self.answer, Exception):
            raise self.answer
        message = SimpleNamespace(content=self.answer)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)


def interpreter_answering(answer: str | Exception) -> VoxtralOrderInterpreter:
    return VoxtralOrderInterpreter(cast(Mistral, SimpleNamespace(chat=FakeChat(answer))))


def test_interpret_returns_one_npc_order_per_answered_action() -> None:
    answer = json.dumps({"npc_name": "Robin", "npc_id": 2, "action": "shoot", "voice_line": "Aim!"})

    orders = interpreter_answering(answer).interpret(b"RIFF")

    assert orders == [
        NpcOrder(npc_id=2, npc_name="Robin", action_type=ActionType.SHOOT, voice_line="Aim!")
    ]


@pytest.mark.parametrize(
    "build_interpreter",
    [
        lambda: interpreter_answering(ConnectionError("network down")),
        lambda: interpreter_answering("{not json"),
        VoxtralOrderInterpreter,
    ],
    ids=["client-failure", "unparsable-answer", "missing-api-key"],
)
def test_interpret_raises_only_the_port_error_without_the_vendor_text(
    build_interpreter: Callable[[], VoxtralOrderInterpreter], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    with pytest.raises(OrderInterpretationError) as raised:
        build_interpreter().interpret(b"RIFF")

    assert "network down" not in str(raised.value)
