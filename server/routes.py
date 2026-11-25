"""HTTP routes and Socket.IO events of the client contract (`docs/api.md`)."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request, send_from_directory
from flask.typing import ResponseReturnValue
from flask_socketio import SocketIO, emit
from werkzeug.exceptions import RequestEntityTooLarge

from game.orders.direct_orders import DirectOrder, DirectOrderOutcome
from server.constants import ENGINE_EXTENSION, MAX_REQUEST_BYTES, MIN_AUDIO_BYTES
from server.engine import GameEngine
from server.request_bodies import (
    InvalidRequestError,
    parse_action_order,
    parse_audio_base64,
    parse_command_text,
    parse_discard_amounts,
    parse_model_id,
    parse_move_order,
    parse_selected_npc_id,
)

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
    """Enqueue a direct action. Body: {"npcId": 1, "action": "chop_wood", "target"?: [col, row]}."""
    return _answer_direct_order(parse_action_order(_json_body()))


@routes.route("/api/select", methods=["POST"])
def post_select() -> ResponseReturnValue:
    """Select an NPC, or deselect all with ``{}``. Body: {"npcId": 1}."""
    npc_id = parse_selected_npc_id(_json_body())
    if npc_id is None:
        _engine().deselect_all()
    elif not _engine().select_npc(npc_id):
        return _refuse(f"unknown npcId: {npc_id}")
    return jsonify({"ok": True})


@routes.route("/api/move", methods=["POST"])
def post_move() -> ResponseReturnValue:
    """Move an NPC. Body: {"npcId": 1, "col": 10, "row": 5}."""
    return _answer_direct_order(parse_move_order(_json_body()))


@routes.route("/api/discard", methods=["POST"])
def post_discard() -> Response:
    """Discard from storage. Body: {"wood": 5, "stone": 3, "gold": 0, "wheat": 2}, each optional, none negative."""
    discarded = _engine().discard_resources(parse_discard_amounts(_json_body()))
    return jsonify({"ok": True, "discarded": discarded})


@routes.route("/api/dismiss_storage", methods=["POST"])
def post_dismiss_storage() -> Response:
    released = _engine().release_npcs_waiting_deposit()
    return jsonify({"ok": True, "released": released})


@routes.route("/api/audio", methods=["POST"])
def post_audio() -> ResponseReturnValue:
    """Interpret a voice command. Body: multipart field "audio", or JSON {"audio_b64": "<base64 WAV>"}."""
    upload = request.files.get("audio")
    wav_bytes = upload.read() if upload is not None else parse_audio_base64(_json_body())
    if len(wav_bytes) < MIN_AUDIO_BYTES:
        return _refuse("no audio data received")
    if not _engine().send_audio_command(wav_bytes):
        return _refuse("the selected model takes no voice commands")
    return jsonify({"ok": True})


@routes.route("/api/command", methods=["POST"])
def post_command() -> ResponseReturnValue:
    """Interpret a typed command. Body: {"text": "<command>"}."""
    _engine().send_text_command(parse_command_text(_json_body()))
    return jsonify({"ok": True})


@routes.route("/api/model", methods=["POST"])
def post_model() -> ResponseReturnValue:
    """Pick the model of the next commands. Body: {"modelId": "<catalog id>"}."""
    model_id = parse_model_id(_json_body())
    if not _engine().select_model(model_id):
        return _refuse(f"unknown or unavailable modelId: {model_id!r}")
    return jsonify({"ok": True})


@routes.before_request
def refuse_cross_origin_request() -> ResponseReturnValue | None:
    """Answer 403 to a browser request sent by a page of another origin.

    Browsers send `Origin` on cross-origin requests, including the form and
    `text/plain` POSTs that skip the CORS preflight. A request without it (curl, the
    test client) is not a browser page and goes through.
    """
    origin = request.headers.get("Origin")
    if origin is not None and origin != request.host_url.rstrip("/"):
        return jsonify({"error": "cross-origin request refused"}), 403
    return None


@routes.errorhandler(InvalidRequestError)
def answer_invalid_request(error: InvalidRequestError) -> ResponseReturnValue:
    return _refuse(str(error))


@routes.errorhandler(RequestEntityTooLarge)
def answer_request_too_large(_: RequestEntityTooLarge) -> ResponseReturnValue:
    return jsonify({"error": f"body larger than {MAX_REQUEST_BYTES} bytes"}), 413


def _json_body() -> object:
    # silent: a body that is not JSON, or not sent as application/json, reads as None
    # and is refused by the parser; force=True would accept text/plain cross-site posts.
    return request.get_json(silent=True)


def _answer_direct_order(order: DirectOrder) -> ResponseReturnValue:
    outcome = _engine().give_direct_order(order)
    if outcome is DirectOrderOutcome.UNKNOWN_NPC:
        return _refuse(f"unknown npcId: {order.npc_id}")
    if outcome is DirectOrderOutcome.TARGET_OUTSIDE_MAP:
        return _refuse(f"target outside the map: {order.target}")
    # REFUSED_BY_NPC: the NPC answers "I can't do that!" in the game; the request was valid.
    return jsonify({"ok": True})


def _refuse(message: str) -> ResponseReturnValue:
    return jsonify({"error": message}), 400


def register_socket_events(socketio: SocketIO, engine: GameEngine) -> None:
    @socketio.on("connect")  # type: ignore[untyped-decorator]
    def on_connect() -> None:
        """Send the state on connect so the client renders before the next push."""
        emit("state", engine.get_state())
