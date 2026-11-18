"""Drive the HTTP contract of docs/api.md through the Flask app, as the browser client does."""

import io
from typing import Any

import pytest
from flask.testing import FlaskClient

from game.settings import MAP_COLS, MAP_ROWS
from server.constants import MIN_AUDIO_BYTES
from server.engine import GameEngine


def read_state(client: FlaskClient) -> dict[str, Any]:
    response = client.get("/api/state")
    assert response.status_code == 200
    state: dict[str, Any] = response.get_json()
    return state


def first_controllable_npc(client: FlaskClient) -> dict[str, Any]:
    return next(npc for npc in read_state(client)["npcs"] if npc["controllable"])


def test_state_exposes_every_top_level_section(client: FlaskClient) -> None:
    state = read_state(client)

    assert set(state) >= {"map", "resources", "npcs", "fauna", "arrows", "storage", "log"}
    assert len(state["map"]["tiles"]) == state["map"]["rows"]
    assert state["npcs"]


def test_select_marks_the_npc_then_empty_body_deselects_all(client: FlaskClient) -> None:
    npc_id = first_controllable_npc(client)["id"]

    client.post("/api/select", json={"npcId": npc_id})
    assert [npc["id"] for npc in read_state(client)["npcs"] if npc["selected"]] == [npc_id]

    client.post("/api/select", json={})
    assert not any(npc["selected"] for npc in read_state(client)["npcs"])


def test_move_enqueues_an_action_on_the_npc(client: FlaskClient, engine: GameEngine) -> None:
    npc = first_controllable_npc(client)

    response = client.post(
        "/api/move", json={"npcId": npc["id"], "col": npc["tileCol"], "row": npc["tileRow"] + 1}
    )

    assert response.get_json() == {"ok": True}
    assert engine._find_npc(npc["id"]).queue_size == npc["queueSize"] + 1  # type: ignore[union-attr]


@pytest.mark.parametrize("action", ["dance", ["chop_wood"], {"name": "chop_wood"}])
def test_action_outside_the_action_names_is_refused(
    client: FlaskClient, engine: GameEngine, action: object
) -> None:
    npc = first_controllable_npc(client)

    response = client.post("/api/action", json={"npcId": npc["id"], "action": action})

    assert response.status_code == 400
    assert "unknown action" in response.get_json()["error"]
    assert engine._find_npc(npc["id"]).queue_size == npc["queueSize"]  # type: ignore[union-attr]


UNKNOWN_NPC_ID = 999_999


@pytest.mark.parametrize(
    ("route", "body"),
    [
        ("/api/select", [1]),
        ("/api/select", {"npcId": "1"}),
        ("/api/select", {"npcId": True}),
        ("/api/select", {"npcId": UNKNOWN_NPC_ID}),
        ("/api/discard", [1]),
        ("/api/discard", {"wood": -1}),
        ("/api/discard", {"wood": "3"}),
        ("/api/discard", {"wood": 1.5}),
        ("/api/discard", {"iron": 2}),
        ("/api/move", {"npcId": 1, "col": 3}),
        ("/api/move", {"npcId": 1, "col": "x", "row": 2}),
        ("/api/move", {"npcId": UNKNOWN_NPC_ID, "col": 1, "row": 1}),
        ("/api/move", {"npcId": 1, "col": MAP_COLS, "row": 1}),
        ("/api/move", {"npcId": 1, "col": 1, "row": -1}),
        ("/api/action", {"action": "chop_wood"}),
        ("/api/action", {"npcId": UNKNOWN_NPC_ID, "action": "eat"}),
        ("/api/action", {"npcId": 1, "action": "move_to"}),
        ("/api/action", {"npcId": 1, "action": "move_to", "target": [1]}),
        ("/api/action", {"npcId": 1, "action": "move_to", "target": [1, "2"]}),
        ("/api/action", {"npcId": 1, "action": "build", "target": [0, MAP_ROWS]}),
        ("/api/audio", {}),
        ("/api/audio", {"audio_b64": 3}),
        ("/api/audio", {"audio_b64": "c2hvcnQ="}),
        ("/api/audio", {"audio_b64": "not base64!"}),
        ("/api/audio", {"audio_b64": "é"}),
    ],
)
def test_invalid_request_is_refused(client: FlaskClient, route: str, body: object) -> None:
    response = client.post(route, json=body)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_body_not_sent_as_json_is_refused(client: FlaskClient) -> None:
    response = client.post("/api/select", data="{}", content_type="text/plain")

    assert response.status_code == 400
    assert response.get_json() == {"error": "body must be a JSON object"}


def test_multipart_audio_without_its_file_names_both_accepted_forms(client: FlaskClient) -> None:
    response = client.post("/api/audio", data={"other": "x"})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "multipart audio file or JSON audio_b64 string required"
    }


def test_uploaded_audio_is_sent_to_the_engine(client: FlaskClient, engine: GameEngine) -> None:
    response = client.post(
        "/api/audio", data={"audio": (io.BytesIO(bytes(MIN_AUDIO_BYTES)), "a.wav")}
    )

    assert response.get_json() == {"ok": True}
    assert engine.log_messages[-1] == "Listening..."


def test_discard_removes_only_what_storage_holds(client: FlaskClient, engine: GameEngine) -> None:
    engine.storage.add("wood", 5)

    response = client.post("/api/discard", json={"wood": 8, "stone": 2})

    assert response.get_json() == {"ok": True, "discarded": {"wood": 5}}
    assert read_state(client)["storage"]["wood"] == 0


def test_dismiss_storage_reports_no_release_when_nobody_waits(client: FlaskClient) -> None:
    response = client.post("/api/dismiss_storage")

    assert response.get_json() == {"ok": True, "released": 0}


def test_index_serves_the_client(client: FlaskClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert b"<canvas" in response.data
