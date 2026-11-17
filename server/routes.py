"""HTTP routes and Socket.IO events of the client contract (`docs/api.md`)."""

from __future__ import annotations

import base64

from flask import Blueprint, Response, current_app, jsonify, request, send_from_directory
from flask.typing import ResponseReturnValue
from flask_socketio import SocketIO, emit

from game.constants import STORED_RESOURCE_KINDS
from server.constants import ENGINE_EXTENSION
from server.engine import GameEngine

routes = Blueprint("routes", __name__)


def _engine() -> GameEngine:
    engine: GameEngine = current_app.extensions[ENGINE_EXTENSION]
    return engine


@routes.route("/")
def index() -> Response:
    return send_from_directory("static", "index.html")


@routes.route("/static/<path:path>")
def static_files(path: str) -> Response:
    return send_from_directory("static", path)


@routes.route("/favicon.ico")
def favicon() -> Response:
    return send_from_directory("static", "favicon.svg")


@routes.route("/api/state")
def get_state() -> Response:
    return jsonify(_engine().get_state())


@routes.route("/api/action", methods=["POST"])
def post_action() -> ResponseReturnValue:
    """Enqueue a direct action. Body: {"npcId": 1, "action": "chop_wood", "target": [col, row]?}."""
    data = request.get_json(force=True)
    npc_id = data.get("npcId")
    action = data.get("action", "")
    target = data.get("target")
    if npc_id is None:
        return jsonify({"error": "npcId required"}), 400
    _engine().enqueue_action(npc_id, action, target)
    return jsonify({"ok": True})


@routes.route("/api/select", methods=["POST"])
def post_select() -> Response:
    """Select an NPC, or deselect all without ``npcId``. Body: {"npcId": 1}."""
    data = request.get_json(force=True)
    npc_id = data.get("npcId")
    if npc_id is not None:
        _engine().select_npc(npc_id)
    else:
        _engine().deselect_all()
    return jsonify({"ok": True})


@routes.route("/api/move", methods=["POST"])
def post_move() -> ResponseReturnValue:
    """Move an NPC. Body: {"npcId": 1, "col": 10, "row": 5}."""
    data = request.get_json(force=True)
    npc_id = data.get("npcId")
    col = data.get("col")
    row = data.get("row")
    if npc_id is None or col is None or row is None:
        return jsonify({"error": "npcId, col, row required"}), 400
    _engine().enqueue_action(npc_id, "move_to", [col, row])
    return jsonify({"ok": True})


@routes.route("/api/discard", methods=["POST"])
def post_discard() -> Response:
    """Discard from storage. Body: {"wood": 5, "stone": 3, "gold": 0, "wheat": 2}, each optional."""
    data = request.get_json(force=True)
    amounts = {
        resource: int(amount)
        for resource in STORED_RESOURCE_KINDS
        if isinstance(amount := data.get(resource, 0), (int, float)) and amount > 0
    }
    discarded = _engine().discard_resources(amounts)
    return jsonify({"ok": True, "discarded": discarded})


@routes.route("/api/dismiss_storage", methods=["POST"])
def post_dismiss_storage() -> Response:
    released = _engine().release_npcs_waiting_deposit()
    return jsonify({"ok": True, "released": released})


@routes.route("/api/audio", methods=["POST"])
def post_audio() -> ResponseReturnValue:
    """Interpret a voice command. Body: multipart field "audio", or JSON {"audio_b64": "<base64 WAV>"}."""
    wav_bytes = None
    if "audio" in request.files:
        wav_bytes = request.files["audio"].read()
    else:
        data = request.get_json(force=True, silent=True) or {}
        b64 = data.get("audio_b64", "")
        if b64:
            wav_bytes = base64.b64decode(b64)

    if not wav_bytes or len(wav_bytes) < 100:
        return jsonify({"error": "no audio data received"}), 400

    _engine().send_audio_command(wav_bytes)
    return jsonify({"ok": True})


def register_socket_events(socketio: SocketIO, engine: GameEngine) -> None:
    @socketio.on("connect")  # type: ignore[untyped-decorator]
    def on_connect() -> None:
        """Send the state on connect so the client renders before the next push."""
        emit("state", engine.get_state())
