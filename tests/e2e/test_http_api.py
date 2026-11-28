"""Drive the HTTP contract of docs/api.md through the Flask app, as the browser client does."""

import base64
import io
import os
from typing import Any

import pytest
from flask.testing import FlaskClient

from game.settings import MAP_COLS, MAP_ROWS
from server.app import create_app
from server.constants import (
    MAX_COMMAND_CHARACTERS,
    MAX_REQUEST_BYTES,
    MIN_AUDIO_BYTES,
)
from server.engine import GameEngine
from tests.fakes import ScriptedOrderInterpreter


def read_state(client: FlaskClient) -> dict[str, Any]:
    response = client.get("/api/state")
    assert response.status_code == 200
    state: dict[str, Any] = response.get_json()
    return state


def first_controllable_npc(client: FlaskClient) -> dict[str, Any]:
    return next(npc for npc in read_state(client)["npcs"] if npc["controllable"])


def read_npc(client: FlaskClient, npc_id: int) -> dict[str, Any]:
    return next(npc for npc in read_state(client)["npcs"] if npc["id"] == npc_id)


def test_state_exposes_every_top_level_section(client: FlaskClient) -> None:
    state = read_state(client)

    assert set(state) >= {
        "map",
        "resources",
        "npcs",
        "fauna",
        "arrows",
        "storage",
        "log",
        "chat",
        "hasVoiceInput",
    }
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
    col, row = engine._find_npc(npc["id"]).tile_pos  # type: ignore[union-attr]

    response = client.post("/api/move", json={"npcId": npc["id"], "col": col, "row": row + 1})

    assert response.get_json() == {"ok": True}
    assert (npc["actionType"], read_npc(client, npc["id"])["actionType"]) == ("", "move_to")


@pytest.mark.parametrize("action", ["dance", ["chop_wood"], {"name": "chop_wood"}])
def test_action_outside_the_action_names_is_refused(client: FlaskClient, action: object) -> None:
    npc = first_controllable_npc(client)

    response = client.post("/api/action", json={"npcId": npc["id"], "action": action})

    assert response.status_code == 400
    assert "unknown action" in response.get_json()["error"]
    assert read_npc(client, npc["id"])["actionType"] == npc["actionType"]


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
        ("/api/command", {}),
        ("/api/command", {"text": 3}),
        ("/api/command", {"text": " \n "}),
        ("/api/command", {"text": "a" * (MAX_COMMAND_CHARACTERS + 1)}),
        ("/api/model", {}),
        ("/api/model", {"modelId": 3}),
        ("/api/model", {"modelId": "gpt-unknown"}),
        ("/api/model", {"modelId": "codestral-latest"}),
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


def test_body_over_the_size_limit_is_refused(client: FlaskClient) -> None:
    response = client.post(
        "/api/audio", data={"audio": (io.BytesIO(bytes(MAX_REQUEST_BYTES)), "a.wav")}
    )

    assert response.status_code == 413
    assert "error" in response.get_json()


def test_multipart_audio_without_its_file_names_both_accepted_forms(client: FlaskClient) -> None:
    response = client.post("/api/audio", data={"other": "x"})

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "multipart audio file or JSON audio_b64 string required"
    }


def test_uploaded_audio_is_sent_to_the_interpreter(
    client: FlaskClient, interpreter: ScriptedOrderInterpreter
) -> None:
    response = client.post(
        "/api/audio", data={"audio": (io.BytesIO(bytes(MIN_AUDIO_BYTES)), "a.wav")}
    )

    assert response.get_json() == {"ok": True}
    assert interpreter.commands == [bytes(MIN_AUDIO_BYTES)]


def test_a_typed_command_is_sent_stripped_to_the_interpreter(
    client: FlaskClient, interpreter: ScriptedOrderInterpreter
) -> None:
    command = "a" * MAX_COMMAND_CHARACTERS

    response = client.post("/api/command", json={"text": f"  {command}\n"})

    assert response.get_json() == {"ok": True}
    assert interpreter.commands == [command]


def test_the_state_lists_the_available_models_and_the_selected_one(client: FlaskClient) -> None:
    state = read_state(client)

    assert state["models"] == [
        {
            "id": "voxtral-small-latest",
            "name": "Voxtral Small",
            "hasVoiceInput": True,
        },
        {
            "id": "mistral-small-latest",
            "name": "Mistral Small 4",
            "hasVoiceInput": False,
        },
    ]
    assert (state["selectedModelId"], state["hasVoiceInput"]) == ("voxtral-small-latest", True)


def test_a_picked_model_takes_the_next_command(
    client: FlaskClient, interpreter: ScriptedOrderInterpreter
) -> None:
    response = client.post("/api/model", json={"modelId": "mistral-small-latest"})
    client.post("/api/command", json={"text": "Bob, chop wood"})

    assert response.get_json() == {"ok": True}
    assert interpreter.model_ids == ["mistral-small-latest"]
    assert read_state(client)["selectedModelId"] == "mistral-small-latest"


def test_audio_is_refused_when_the_selected_model_takes_no_voice_commands(
    client: FlaskClient,
) -> None:
    client.post("/api/model", json={"modelId": "mistral-small-latest"})

    response = client.post(
        "/api/audio", data={"audio": (io.BytesIO(bytes(MIN_AUDIO_BYTES)), "a.wav")}
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "the selected model takes no voice commands"}
    assert read_state(client)["hasVoiceInput"] is False


@pytest.mark.parametrize(
    ("origin", "expected_status"),
    [(None, 200), ("http://localhost:8000", 200), ("http://evil.example", 403), ("null", 403)],
)
def test_only_the_served_origin_may_post(
    client: FlaskClient, origin: str | None, expected_status: int
) -> None:
    headers = {} if origin is None else {"Origin": origin}

    response = client.post("/api/dismiss_storage", headers=headers)

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    ("origin", "expected_status"),
    [("http://localhost:8000", 200), ("http://evil.example", 400), ("null", 400)],
)
def test_only_the_served_origin_may_open_a_socket(
    client: FlaskClient, origin: str, expected_status: int
) -> None:
    response = client.get("/socket.io/?EIO=4&transport=polling", headers={"Origin": origin})

    assert response.status_code == expected_status


@pytest.mark.parametrize("host", ["localhost:8000", "127.0.0.1:8000", "LOCALHOST:8000"])
def test_a_served_host_is_answered(client: FlaskClient, host: str) -> None:
    response = client.get("/api/state", headers={"Host": host})

    assert response.status_code == 200


# DNS rebinding: the attacker's page re-resolves to this server and sends its own
# domain as Host, with an Origin equal to it (or none on a same-origin GET).
_REBOUND_HOST = "evil.example:8000"
_REBOUND = {"Host": _REBOUND_HOST}
_POLLING = "/socket.io/?EIO=4&transport=polling"
_WEBSOCKET_UPGRADE = {
    "Upgrade": "websocket",
    "Connection": "Upgrade",
    # A fresh 16-byte nonce, as RFC 6455 asks of a client.
    "Sec-WebSocket-Key": base64.b64encode(os.urandom(16)).decode(),
    "Sec-WebSocket-Version": "13",
}


@pytest.mark.parametrize(
    ("method", "path", "headers"),
    [
        pytest.param(
            "POST",
            "/api/dismiss_storage",
            _REBOUND | {"Origin": f"http://{_REBOUND_HOST}"},
            id="route-with-origin",
        ),
        pytest.param("GET", "/api/state", _REBOUND, id="route-without-origin"),
        pytest.param("GET", "/", _REBOUND, id="static"),
        pytest.param(
            "GET",
            _POLLING,
            _REBOUND | {"Origin": f"http://{_REBOUND_HOST}"},
            id="polling-with-origin",
        ),
        pytest.param("GET", _POLLING, _REBOUND, id="polling-without-origin"),
        pytest.param(
            "GET",
            "/socket.io/?EIO=4&transport=websocket",
            _REBOUND | _WEBSOCKET_UPGRADE,
            id="websocket-upgrade",
        ),
        pytest.param(
            "GET",
            "/api/state",
            _REBOUND | {"X-Forwarded-Host": "localhost:8000"},
            id="forwarded-host-ignored",
        ),
        pytest.param("GET", "/api/state", {"Host": ""}, id="empty-host"),
        pytest.param("GET", "/api/state", {"Host": "localhost.:8000"}, id="trailing-dot"),
        pytest.param("GET", "/api/state", {"Host": "localhost:8001"}, id="wrong-port"),
        pytest.param("GET", "/api/state", {"Host": "localhost"}, id="no-port"),
    ],
)
def test_a_host_outside_the_allowlist_is_refused_with_403(
    client: FlaskClient, method: str, path: str, headers: dict[str, str]
) -> None:
    response = client.open(path, method=method, headers=headers)

    assert response.status_code == 403
    assert response.get_json() == {"error": "host not allowed"}


def test_a_network_bind_allows_its_address_and_not_loopback(engine: GameEngine) -> None:
    app, _ = create_app(engine, served_host="192.168.1.20")
    client = app.test_client()

    served = client.get("/api/state", headers={"Host": "192.168.1.20:8000"})
    loopback = client.get("/api/state", headers={"Host": "localhost:8000"})

    assert (served.status_code, loopback.status_code) == (200, 403)


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
