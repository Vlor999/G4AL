"""Flask + Socket.IO backend – pushes game state via WebSocket.

The Python game engine (map, NPCs, entities, storage) runs in a
background thread at ~60 FPS.  State is pushed to all connected
clients via Socket.IO.  Actions arrive via REST or socket events.
"""

from __future__ import annotations

import base64
import os
import time
import threading
from pathlib import Path
from typing import List, Optional

# ── dotenv ───────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# ── Headless pygame init (no display, but REAL audio for TTS) ────────────
os.environ["SDL_VIDEODRIVER"] = "dummy"
# NOTE: Do NOT set SDL_AUDIODRIVER=dummy — we need real audio for TTS playback
import pygame
pygame.init()
pygame.mixer.init()  # ensure mixer is ready for TTS mp3 playback
# Create a tiny hidden surface so pygame.font and Surface work
pygame.display.set_mode((1, 1))

from game.settings import (
    TILE_SIZE, FPS,
    TTS_MAX_SPEAKERS,
)
from game.map import GameMap
from game.entities import Resource, spawn_resources, Rock, Structure, WheatField
from game.storage import ResourceStorage
from game.npc import NPC, Action, ActionType
from api.logger import pipeline_logger
from api.tts import TTSEngine

# Lazy-import LLM
try:
    from api.interpreter import (
        interpret_command,
        interpret_audio_command,
        register_npcs,
        CommandResponse,
    )
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False

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
}


class GameEngine:
    """Headless game engine – no rendering, just logic at ~60 FPS."""

    def __init__(self):
        self.game_map = GameMap(seed=42)
        self.storage = ResourceStorage()
        self.resources: List[Resource] = spawn_resources(self.game_map)
        self.npcs: List[NPC] = []
        self.tts = TTSEngine()
        self.log_messages: list[str] = []
        self._lock = threading.Lock()
        self._running = False
        self._pending_response: Optional[CommandResponse] = None

        self._spawn_initial_npcs(3)
        self._sync_npc_roster()

    def _spawn_initial_npcs(self, count: int):
        cx, cy = self.game_map.cols // 2, self.game_map.rows // 2
        entity_tiles = {(r.col, r.row) for r in self.resources}
        placed = 0
        for dc in range(-3, 4):
            for dr in range(-3, 4):
                c, r = cx + dc, cy + dr
                if self.game_map.is_walkable(c, r) and (c, r) not in entity_tiles:
                    wx, wy = self.game_map.tile_center(c, r)
                    npc = NPC(
                        wx, wy, self.game_map, self.resources,
                        self.storage, all_npcs=self.npcs,
                    )
                    self.npcs.append(npc)
                    entity_tiles.add((c, r))
                    placed += 1
                    if placed >= count:
                        return

    def _sync_npc_roster(self):
        if not _HAS_LLM:
            return
        register_npcs([{"id": n.id, "name": n.name} for n in self.npcs])

    def _add_log(self, msg: str):
        self.log_messages.append(msg)
        if len(self.log_messages) > 50:
            self.log_messages.pop(0)

    # ── tick ─────────────────────────────────────────────────────────────

    def tick(self):
        """One frame of game logic."""
        with self._lock:
            # Apply pending LLM response
            if self._pending_response is not None:
                self._apply_pending_response()

            for npc in self.npcs:
                npc.update()

            for r in self.resources:
                if isinstance(r, WheatField):
                    r.grow_tick()

    # ── commands ─────────────────────────────────────────────────────────

    def enqueue_action(self, npc_id: int, action_str: str, target=None):
        """Enqueue an action on an NPC by ID."""
        action_type = _ACTION_MAP.get(action_str)
        if not action_type:
            return
        with self._lock:
            npc = self._find_npc(npc_id)
            if not npc:
                return
            if action_type in (ActionType.BUILD, ActionType.PLANT_WHEAT):
                t = tuple(target) if target else npc.tile_pos
                npc.enqueue(Action(action_type, target=t))
            elif action_type == ActionType.MOVE_TO:
                if target:
                    npc.enqueue(Action(action_type, target=tuple(target)))
            else:
                npc.enqueue(Action(action_type))

    def select_npc(self, npc_id: int):
        with self._lock:
            for n in self.npcs:
                n.selected = (n.id == npc_id)

    def deselect_all(self):
        with self._lock:
            for n in self.npcs:
                n.selected = False

    def send_text_command(self, text: str):
        """Process a natural language command via LLM (runs in bg thread)."""
        if not _HAS_LLM:
            self._add_log("LLM not available")
            return
        self._add_log("Thinking...")
        threading.Thread(
            target=self._llm_worker, args=(text,), daemon=True
        ).start()

    def _llm_worker(self, text: str):
        result = interpret_command(text)
        with self._lock:
            self._pending_response = result

    def _apply_pending_response(self):
        response = self._pending_response
        self._pending_response = None
        if response is None or not response.actions:
            self._add_log("No actions understood.")
            return

        from dataclasses import asdict
        pipeline_logger.pipeline_summary(voice_text="", order=asdict(response))

        spoken_count = 0
        for order in response.actions:
            npc = self._find_npc(order.npc_id)
            if npc is None and self.npcs:
                npc = self.npcs[0]
            if npc is None:
                continue

            action_type = _ACTION_MAP.get(order.action)
            if action_type:
                if action_type in (ActionType.BUILD, ActionType.PLANT_WHEAT):
                    npc.enqueue(Action(action_type, target=npc.tile_pos))
                else:
                    npc.enqueue(Action(action_type))

            npc.say(order.voice_line, duration_frames=360)
            if spoken_count < TTS_MAX_SPEAKERS:
                self.tts.speak(order.voice_line, order.npc_name)
                spoken_count += 1
            self._add_log(f'{order.npc_name}: "{order.voice_line}"')

    def _find_npc(self, npc_id: int) -> Optional[NPC]:
        for n in self.npcs:
            if n.id == npc_id:
                return n
        return None

    # ── state snapshot ───────────────────────────────────────────────────

    def get_state(self) -> dict:
        """Return full game state as a JSON-serializable dict."""
        with self._lock:
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
                "storage": self.storage.snapshot(),
                "log": list(self.log_messages[-20:]),
            }

    def _serialize_resources(self) -> list[dict]:
        result = []
        for r in self.resources:
            if r.depleted:
                continue
            d = {
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
            elif isinstance(r, WheatField):
                d["fullyGrown"] = r.fully_grown
                d["growthRatio"] = round(r.growth_ratio, 2)
            result.append(d)
        return result

    def _serialize_npcs(self) -> list[dict]:
        result = []
        for n in self.npcs:
            result.append({
                "id": n.id,
                "name": n.name,
                "x": round(n.x, 1),
                "y": round(n.y, 1),
                "tileCol": n.tile_pos[0],
                "tileRow": n.tile_pos[1],
                "health": round(n.health, 1),
                "maxHealth": n.max_health,
                "hunger": round(n.hunger, 1),
                "maxHunger": n.max_hunger,
                "state": n.state.name,
                "selected": n.selected,
                "speechText": n._speech_text if n._speech_timer > 0 else "",
                "queueSize": n.queue_size,
            })
        return result

    # ── audio command ─────────────────────────────────────────────────

    def send_audio_command(self, wav_bytes: bytes):
        """Process a voice command via Voxtral (runs in bg thread)."""
        if not _HAS_LLM:
            self._add_log("LLM not available")
            return
        self._add_log("Listening...")
        threading.Thread(
            target=self._audio_worker, args=(wav_bytes,), daemon=True
        ).start()

    def _audio_worker(self, wav_bytes: bytes):
        result = interpret_audio_command(wav_bytes)
        with self._lock:
            self._pending_response = result

    # ── background loop ──────────────────────────────────────────────────

    _frame_count: int = 0
    _ws_push_interval: int = 3  # push state every N frames (~20 Hz at 60 FPS)

    def run_loop(self, socketio_ref=None):
        """Run game tick loop at ~60 FPS in the current thread."""
        self._running = True
        self._frame_count = 0
        target_dt = 1.0 / FPS
        while self._running:
            t0 = time.perf_counter()
            self.tick()
            self._frame_count += 1

            # Push state via WebSocket every few frames
            if socketio_ref and self._frame_count % self._ws_push_interval == 0:
                try:
                    socketio_ref.emit("state", self.get_state(), namespace="/")
                except Exception:
                    pass

            elapsed = time.perf_counter() - t0
            sleep_time = target_dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self):
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
def index():
    return send_from_directory("static", "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ── API endpoints ────────────────────────────────────────────────────────

@app.route("/api/state")
def get_state():
    """Return full game state as JSON (polled by frontend)."""
    return jsonify(engine.get_state())


@app.route("/api/action", methods=["POST"])
def post_action():
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


@app.route("/api/command", methods=["POST"])
def post_command():
    """Send a natural language command to the LLM interpreter.

    Body: { "text": "Tomas go chop wood!" }
    """
    data = request.get_json(force=True)
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    engine.send_text_command(text)
    return jsonify({"ok": True})


@app.route("/api/select", methods=["POST"])
def post_select():
    """Select an NPC.  Body: { "npcId": 1 }"""
    data = request.get_json(force=True)
    npc_id = data.get("npcId")
    if npc_id is not None:
        engine.select_npc(npc_id)
    else:
        engine.deselect_all()
    return jsonify({"ok": True})


@app.route("/api/move", methods=["POST"])
def post_move():
    """Right-click move.  Body: { "npcId": 1, "col": 10, "row": 5 }"""
    data = request.get_json(force=True)
    npc_id = data.get("npcId")
    col = data.get("col")
    row = data.get("row")
    if npc_id is None or col is None or row is None:
        return jsonify({"error": "npcId, col, row required"}), 400
    engine.enqueue_action(npc_id, "move_to", [col, row])
    return jsonify({"ok": True})


@app.route("/api/audio", methods=["POST"])
def post_audio():
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

@socketio.on("connect")
def on_connect():
    """Send full state immediately on connect so client renders instantly."""
    emit("state", engine.get_state())


def main():
    # Start game loop in background (pass socketio so it can push state)
    game_thread = threading.Thread(
        target=engine.run_loop, args=(socketio,), daemon=True
    )
    game_thread.start()

    print("\n  G4AL Web UI → http://127.0.0.1:5000\n")
    try:
        socketio.run(app, host="0.0.0.0", port=5000,
                     debug=False, use_reloader=False,
                     allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()


if __name__ == "__main__":
    main()
