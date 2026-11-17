"""Builds the Flask + Socket.IO app around a game engine and starts the server."""

from __future__ import annotations

import os
import threading

import pygame
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from api.interpreter import VoxtralOrderInterpreter
from api.tts import TTSEngine
from server.constants import ENGINE_EXTENSION, PROJECT_ROOT
from server.engine import GameEngine
from server.routes import register_socket_events, routes


def create_app(engine: GameEngine) -> tuple[Flask, SocketIO]:
    """Serve ``engine`` over HTTP and Socket.IO; starts no thread."""
    app = Flask(__name__, root_path=str(PROJECT_ROOT), static_folder="static")
    app.extensions[ENGINE_EXTENSION] = engine
    CORS(app)
    app.register_blueprint(routes)
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
    register_socket_events(socketio, engine)
    return app, socketio


def main() -> None:
    # Before the adapters: TTSEngine reads its API key from the environment.
    load_dotenv(PROJECT_ROOT / ".env")

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    # api/tts.py plays the voice lines through the mixer.
    pygame.mixer.init()

    interpreter = VoxtralOrderInterpreter()
    speaker = TTSEngine()
    engine = GameEngine(interpreter=interpreter, speaker=speaker)
    interpreter.register_roster(engine.npcs)
    app, socketio = create_app(engine)

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
        speaker.close()
