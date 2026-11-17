"""Flask + Socket.IO backend – pushes game state via WebSocket.

The Python game engine (map, NPCs, entities, storage) runs in a
background thread at ~60 FPS.  State is pushed to all connected
clients via Socket.IO.  Actions arrive via REST or socket events.
"""

from __future__ import annotations

import base64
import os
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pygame
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory
from flask.typing import ResponseReturnValue
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from loguru import logger

from api.logger import pipeline_logger
from api.tts import TTSEngine
from game.constants import STORED_RESOURCE_KINDS
from game.entities import Rock, Structure, WheatField
from game.map import GameMap
from game.npc import NPC, Action, ActionType
from game.orders import NpcOrder, apply_orders
from game.settings import FPS, TILE_SIZE
from game.spawning import spawn_world

# Lazy-import LLM
try:
    from api.interpreter import (
        CommandResponse,
        interpret_audio_command,
        register_npcs,
    )

    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False

# Must run before GameEngine() below: TTSEngine reads its API key from the environment.
load_dotenv(Path(__file__).resolve().parent / ".env")

# ── Pygame audio only (for TTS playback — no display needed) ─────────────
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.mixer.init()  # mixer is used by api/tts.py for mp3 playback

# ═══════════════════════════════════════════════════════════════════════════
#  Game Engine (runs in background thread)
# ═══════════════════════════════════════════════════════════════════════════

_ACTION_MAP = {
    "chop_wood": ActionType.CHOP_WOOD,
    "mine_rock": ActionType.MINE_ROCK,
    "build": ActionType.BUILD,
    "move_to": ActionType.MOVE_TO,
    "eat": ActionType.EAT,
    "plant_wheat": ActionType.PLANT_WHEAT,
    "collect_wheat": ActionType.collect_wheat,
    "shoot": ActionType.SHOOT,
    "defend": ActionType.DEFEND,
}


def _to_npc_orders(response: CommandResponse) -> list[NpcOrder]:
    return [
        NpcOrder(
            npc_id=order.npc_id,
            npc_name=order.npc_name,
            action_type=_ACTION_MAP.get(order.action),
            voice_line=order.voice_line,
        )
        for order in response.actions
    ]


class GameEngine:
    """Headless game engine – no rendering, just logic at ~60 FPS."""

    def __init__(self) -> None:
        self.game_map = GameMap(seed=42)
        world = spawn_world(self.game_map)
        self.storage = world.storage
        self.resources = world.resources
        self.storage_hut = world.storage_hut
        self.npcs = world.npcs
        self.fauna = world.fauna
        self.arrows = world.arrows
        self.tts = TTSEngine()
        self.log_messages: list[str] = []
        self._lock = threading.Lock()
        self._running = False
        self._pending_response: CommandResponse | None = None
        self._sync_npc_roster()

    def _sync_npc_roster(self) -> None:
        if not _HAS_LLM:
            return
        register_npcs(
            [
                {
                    "id": n.id,
                    "name": n.name,
                    "kind": n.kind,
                    "allowed_actions": [a.value for a in n.allowed_actions],
                }
                for n in self.npcs
            ]
        )

    def _add_log(self, msg: str) -> None:
        self.log_messages.append(msg)
        if len(self.log_messages) > 50:
            self.log_messages.pop(0)

    # ── tick ─────────────────────────────────────────────────────────────

    def tick(self) -> None:
        """One frame of game logic."""
        with self._lock:
            # Apply pending LLM response
            if self._pending_response is not None:
                self._apply_pending_response()

            for npc in self.npcs:
                npc.update()

            for creature in self.fauna:
                creature.update()

            for r in self.resources:
                if isinstance(r, WheatField):
                    r.grow_tick()

            # Advance arrow projectiles (mutate in-place to keep shared ref)
            for arrow in self.arrows:
                arrow["frame"] += 1
            self.arrows[:] = [a for a in self.arrows if a["frame"] < a["totalFrames"]]

            # Remove dead fauna
            self.fauna = [f for f in self.fauna if f.health > 0]

            # Remove dead NPCs (mutate in-place to keep shared ref with WildArchers)
            dead_npcs = [n for n in self.npcs if n.health <= 0]
            if dead_npcs:
                selected_died = any(n.selected for n in dead_npcs)
                self.npcs[:] = [n for n in self.npcs if n.health > 0]
                # If the selected NPC died, auto-select another one
                if selected_died and self.npcs:
                    self.npcs[0].selected = True

    # ── commands ─────────────────────────────────────────────────────────

    def enqueue_action(
        self, npc_id: int, action_str: str, target: Sequence[int] | None = None
    ) -> None:
        """Enqueue an action on an NPC by ID."""
        action_type = _ACTION_MAP.get(action_str)
        if not action_type:
            return
        with self._lock:
            npc = self._find_npc(npc_id)
            if not npc:
                return
            if action_type in (ActionType.BUILD, ActionType.PLANT_WHEAT):
                t = (target[0], target[1]) if target else npc.tile_pos
                npc.enqueue(Action(action_type, target=t))
            elif action_type == ActionType.MOVE_TO:
                if target:
                    npc.enqueue(Action(action_type, target=(target[0], target[1])))
            else:
                npc.enqueue(Action(action_type))

    def select_npc(self, npc_id: int) -> None:
        with self._lock:
            for n in self.npcs:
                n.selected = n.id == npc_id

    def deselect_all(self) -> None:
        with self._lock:
            for n in self.npcs:
                n.selected = False

    def _apply_pending_response(self) -> None:
        response = self._pending_response
        self._pending_response = None
        if response is None or not response.actions:
            self._add_log("No actions understood.")
            return

        from dataclasses import asdict

        pipeline_logger.pipeline_summary(voice_text="", order=asdict(response))

        for outcome in apply_orders(self.npcs, _to_npc_orders(response)):
            order = outcome.order
            if outcome.is_spoken:
                self.tts.speak(order.voice_line, order.npc_name)
            self._add_log(f'{order.npc_name}: "{order.voice_line}"')

    def discard_resources(self, amounts: Mapping[str, int]) -> dict[str, int]:
        """Discard from storage; returns what was actually removed per resource."""
        with self._lock:
            return self.storage.discard_resources(amounts)

    def release_npcs_waiting_deposit(self) -> int:
        """Make every NPC waiting for storage space drop its load; returns how many did."""
        with self._lock:
            return sum(npc.give_up_waiting_deposit() for npc in self.npcs)

    def _find_npc(self, npc_id: int) -> NPC | None:
        for n in self.npcs:
            if n.id == npc_id:
                return n
        return None

    # ── state snapshot ───────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        """Return full game state as a JSON-serializable dict."""
        with self._lock:
            # Check if any NPC is waiting to deposit (storage full alert)
            from game.npc import State as NpcState

            storage_full_alert = any(n.state == NpcState.WAITING_DEPOSIT for n in self.npcs)
            return {
                "map": {
                    "cols": self.game_map.cols,
                    "rows": self.game_map.rows,
                    "tileSize": TILE_SIZE,
                    "tiles": [
                        [int(self.game_map.tiles[r][c]) for c in range(self.game_map.cols)]
                        for r in range(self.game_map.rows)
                    ],
                },
                "resources": self._serialize_resources(),
                "npcs": self._serialize_npcs(),
                "fauna": self._serialize_fauna(),
                "arrows": self._serialize_arrows(),
                "storage": self.storage.snapshot(),
                "storageFullAlert": storage_full_alert,
                "log": list(self.log_messages[-20:]),
            }

    def _serialize_resources(self) -> list[dict[str, Any]]:
        result = []
        for r in self.resources:
            if r.depleted:
                continue
            d: dict[str, Any] = {
                "kind": r.kind,
                "col": r.col,
                "row": r.row,
                "hp": r.hp,
                "maxHp": r.max_hp,
            }
            if isinstance(r, Rock):
                d["hasGold"] = r.has_gold
            elif isinstance(r, Structure):
                d["built"] = r.built
                d["buildProgress"] = r.build_progress
                d["buildingType"] = r.building_type
                d["gridWidth"] = r.grid_width
                d["gridHeight"] = r.grid_height
            elif isinstance(r, WheatField):
                d["fullyGrown"] = r.fully_grown
                d["growthRatio"] = round(r.growth_ratio, 2)
            result.append(d)
        return result

    def _serialize_npcs(self) -> list[dict[str, Any]]:
        result = []
        for n in self.npcs:
            result.append(
                {
                    "id": n.id,
                    "name": n.name,
                    "kind": n.kind,
                    "controllable": n.controllable,
                    "allowedActions": [a.value for a in n.allowed_actions],
                    "x": round(n.x, 1),
                    "y": round(n.y, 1),
                    "tileCol": n.tile_pos[0],
                    "tileRow": n.tile_pos[1],
                    "health": round(n.health, 1),
                    "maxHealth": n.max_health,
                    "hunger": round(n.hunger, 1),
                    "maxHunger": n.max_hunger,
                    "state": n.state.name,
                    "actionType": n._current_action.action_type.value if n._current_action else "",
                    "selected": n.selected,
                    "speechText": n._speech_text if n._speech_timer > 0 else "",
                    "isFiring": getattr(n, "_is_firing", False),
                    "isDefending": getattr(n, "_defending", False),
                    "queueSize": n.queue_size,
                    "isCarrying": n.is_carrying,
                    "carrying": dict(n.carrying),
                }
            )
        return result

    def _serialize_fauna(self) -> list[dict[str, Any]]:
        result = []
        for f in self.fauna:
            result.append(
                {
                    "id": f.id,
                    "name": f.name,
                    "kind": f.kind,
                    "controllable": False,
                    "x": round(f.x, 1),
                    "y": round(f.y, 1),
                    "tileCol": f.tile_pos[0],
                    "tileRow": f.tile_pos[1],
                    "health": round(f.health, 1),
                    "maxHealth": f.max_health,
                    "state": f.state.name,
                    "isFiring": getattr(f, "_is_firing", False),
                }
            )
        return result

    def _serialize_arrows(self) -> list[dict[str, Any]]:
        result = []
        for a in self.arrows:
            progress = a["frame"] / max(1, a["totalFrames"])
            result.append(
                {
                    "fromX": round(a["fromX"], 1),
                    "fromY": round(a["fromY"], 1),
                    "toX": round(a["toX"], 1),
                    "toY": round(a["toY"], 1),
                    "progress": round(progress, 3),
                    "team": a.get("team", "blue"),
                }
            )
        return result

    # ── audio command ─────────────────────────────────────────────────

    def send_audio_command(self, wav_bytes: bytes) -> None:
        """Process a voice command via Voxtral (runs in bg thread)."""
        if not _HAS_LLM:
            self._add_log("LLM not available")
            return
        self._add_log("Listening...")
        threading.Thread(target=self._audio_worker, args=(wav_bytes,), daemon=True).start()

    def _audio_worker(self, wav_bytes: bytes) -> None:
        result = interpret_audio_command(wav_bytes)
        with self._lock:
            self._pending_response = result

    # ── background loop ──────────────────────────────────────────────────

    _frame_count: int = 0
    _ws_push_interval: int = 3  # push state every N frames (~20 Hz at 60 FPS)

    def run_loop(self, socketio_ref: SocketIO | None = None) -> None:
        """Run game tick loop at ~60 FPS in the current thread."""
        self._running = True
        self._frame_count = 0
        is_push_failing = False
        target_dt = 1.0 / FPS
        while self._running:
            t0 = time.perf_counter()
            self.tick()
            self._frame_count += 1

            # Push state via WebSocket every few frames
            if socketio_ref and self._frame_count % self._ws_push_interval == 0:
                try:
                    socketio_ref.emit("state", self.get_state(), namespace="/")
                except Exception as exc:  # noqa: BLE001 - a failed push must not stop the game loop
                    # Logged once per failure streak: pushes run ~20 times a second.
                    if not is_push_failing:
                        logger.bind(event="state_push").warning(f"State push failed: {exc}")
                    is_push_failing = True
                else:
                    if is_push_failing:
                        logger.bind(event="state_push").info("State push recovered")
                    is_push_failing = False

            elapsed = time.perf_counter() - t0
            sleep_time = target_dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self) -> None:
        self._running = False
        self.tts.close()
        pipeline_logger.close()


# ═══════════════════════════════════════════════════════════════════════════
#  Flask App
# ═══════════════════════════════════════════════════════════════════════════

engine = GameEngine()
app = Flask(__name__, static_folder="static")
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


if __name__ == "__main__":
    main()
