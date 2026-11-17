"""Drive the HTTP contract of docs/api.md through the Flask app, as the browser client does."""

from typing import Any

import pytest
from flask.testing import FlaskClient

import server


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


def test_move_enqueues_an_action_on_the_npc(client: FlaskClient) -> None:
    npc = first_controllable_npc(client)

    response = client.post(
        "/api/move", json={"npcId": npc["id"], "col": npc["tileCol"], "row": npc["tileRow"] + 1}
    )

    assert response.get_json() == {"ok": True}
    assert server.engine._find_npc(npc["id"]).queue_size == npc["queueSize"] + 1  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("route", "body"),
    [
        ("/api/move", {"npcId": 1, "col": 3}),
        ("/api/action", {"action": "chop_wood"}),
        ("/api/audio", {}),
        ("/api/audio", {"audio_b64": "c2hvcnQ="}),
    ],
)
def test_incomplete_request_is_refused(
    client: FlaskClient, route: str, body: dict[str, Any]
) -> None:
    response = client.post(route, json=body)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_discard_removes_only_what_storage_holds(client: FlaskClient) -> None:
    server.engine.storage.add("wood", 5)

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
