import json
from collections.abc import Iterator

import pytest

from api.interpreter import CommandResponse, NPCOrder, _parse_response, register_npcs


@pytest.fixture(autouse=True)
def roster() -> Iterator[None]:
    register_npcs(
        [
            {"id": 1, "name": "Bob", "kind": "pawn", "allowed_actions": ["chop_wood"]},
            {"id": 2, "name": "Robin", "kind": "archer", "allowed_actions": ["shoot"]},
        ]
    )
    yield
    register_npcs([])


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
    assert _parse_response(raw) == CommandResponse(
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
    assert _parse_response(json.dumps(item)).actions == [expected]


def test_parse_response_strips_markdown_fences() -> None:
    raw = '```json\n{"npc_name": "Robin", "action": "defend", "voice_line": "On guard."}\n```'
    assert _parse_response(raw).actions[0].action == "defend"


def test_parse_response_rejects_malformed_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_response("{not json")
