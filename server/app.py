"""Flask + Socket.IO backend – pushes game state via WebSocket.

The Python game engine (map, NPCs, entities, storage) runs in a
background thread at ~60 FPS.  State is pushed to all connected
clients via Socket.IO.  Actions arrive via REST or socket events.
"""

from __future__ import annotations

import base64
import os
import threading

import pygame
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory
from flask.typing import ResponseReturnValue
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from api.interpreter import VoxtralOrderInterpreter
from api.tts import TTSEngine
from game.constants import STORED_RESOURCE_KINDS
from server.constants import PROJECT_ROOT
from server.engine import GameEngine

# Must run before TTSEngine() below: it reads its API key from the environment.
load_dotenv(PROJECT_ROOT / ".env")

# ── Pygame audio only (for TTS playback — no display needed) ─────────────
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.mixer.init()  # mixer is used by api/tts.py for mp3 playback

_interpreter = VoxtralOrderInterpreter()
_speaker = TTSEngine()
engine = GameEngine(interpreter=_interpreter, speaker=_speaker)
_interpreter.register_roster(engine.npcs)
app = Flask(__name__, root_path=str(PROJECT_ROOT), static_folder="static")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# ── Static files ─────────────────────────────────────────────────────────


@app.route("/")
def index() -> Response:
    return send_from_directory("static", "index.html")


@app.route("/static/<path:path>")
def static_files(path: str) -> Response:
    return send_from_directory("static", path)


@app.route("/favicon.ico")
def favicon() -> Response:
    return send_from_directory("static", "favicon.svg")


# ── API endpoints ────────────────────────────────────────────────────────


@app.route("/api/state")
def get_state() -> Response:
    """Return full game state as JSON (polled by frontend)."""
    return jsonify(engine.get_state())


@app.route("/api/action", methods=["POST"])
def post_action() -> ResponseReturnValue:
    """Dispatch a direct action to an NPC.

    Body: { "npcId": 1, "action": "chop_wood", "target": [col, row]? }
    """
    data = request.get_json(force=True)
    npc_id = data.get("npcId")
    action = data.get("action", "")
    target = data.get("target")
    if npc_id is None:
        return jsonify({"error": "npcId required"}), 400
    engine.enqueue_action(npc_id, action, target)
    return jsonify({"ok": True})


@app.route("/api/select", methods=["POST"])
def post_select() -> Response:
    """Select an NPC.  Body: { "npcId": 1 }"""
    data = request.get_json(force=True)
    npc_id = data.get("npcId")
    if npc_id is not None:
        engine.select_npc(npc_id)
    else:
        engine.deselect_all()
    return jsonify({"ok": True})


@app.route("/api/move", methods=["POST"])
def post_move() -> ResponseReturnValue:
    """Right-click move.  Body: { "npcId": 1, "col": 10, "row": 5 }"""
    data = request.get_json(force=True)
    npc_id = data.get("npcId")
    col = data.get("col")
    row = data.get("row")
    if npc_id is None or col is None or row is None:
        return jsonify({"error": "npcId, col, row required"}), 400
    engine.enqueue_action(npc_id, "move_to", [col, row])
    return jsonify({"ok": True})


@app.route("/api/discard", methods=["POST"])
def post_discard() -> Response:
    """Discard resources from storage to free up capacity.

    Body: { "wood": 5, "stone": 3, "gold": 0, "wheat": 2 }
    Each field is optional; only listed resources are discarded.
    """
    data = request.get_json(force=True)
    amounts = {
        resource: int(amount)
        for resource in STORED_RESOURCE_KINDS
        if isinstance(amount := data.get(resource, 0), (int, float)) and amount > 0
    }
    discarded = engine.discard_resources(amounts)
    return jsonify({"ok": True, "discarded": discarded})


@app.route("/api/dismiss_storage", methods=["POST"])
def post_dismiss_storage() -> Response:
    """Release all NPCs stuck in WAITING_DEPOSIT → IDLE."""
    released = engine.release_npcs_waiting_deposit()
    return jsonify({"ok": True, "released": released})


@app.route("/api/audio", methods=["POST"])
def post_audio() -> ResponseReturnValue:
    """Receive recorded audio from browser push-to-talk.

    Accepts either:
      - multipart/form-data with field "audio" (WAV or WebM blob)
      - JSON body with {"audio_b64": "<base64 WAV data>"}
    """
    wav_bytes = None

    # Try multipart file upload first
    if "audio" in request.files:
        wav_bytes = request.files["audio"].read()
    else:
        # Fallback: JSON with base64
        data = request.get_json(force=True, silent=True) or {}
        b64 = data.get("audio_b64", "")
        if b64:
            wav_bytes = base64.b64decode(b64)

    if not wav_bytes or len(wav_bytes) < 100:
        return jsonify({"error": "no audio data received"}), 400

    engine.send_audio_command(wav_bytes)
    return jsonify({"ok": True})


# ═══════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════

# ── Socket.IO events ─────────────────────────────────────────────────────


@socketio.on("connect")  # type: ignore[untyped-decorator]
def on_connect() -> None:
    """Send full state immediately on connect so client renders instantly."""
    emit("state", engine.get_state())


def main() -> None:
    # Start game loop in background (pass socketio so it can push state)
    game_thread = threading.Thread(target=engine.run_loop, args=(socketio,), daemon=True)
    game_thread.start()

    host = os.environ.get("G4AL_HOST", "127.0.0.1")
    print(f"\n  G4AL Web UI → http://{host}:8000\n")
    try:
        socketio.run(
            app,
            host=host,
            port=8000,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True,
        )
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        _speaker.close()


if __name__ == "__main__":
    main()
