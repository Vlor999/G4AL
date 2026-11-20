"""Builds the Flask + Socket.IO app around a game engine and starts the server."""

from __future__ import annotations

import os
import threading

import pygame
from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO

from api.interpreter import MistralOrderInterpreter
from api.logger import PipelineLogger, use_pipeline_sinks
from api.tts import TTSEngine
from server.constants import (
    DEFAULT_SERVED_HOST,
    ENGINE_EXTENSION,
    MAX_REQUEST_BYTES,
    PROJECT_ROOT,
    SERVER_PORT,
)
from server.engine import GameEngine
from server.host_allowlist import (
    HostAllowlistMiddleware,
    UnsupportedServedHostError,
    allowed_hosts,
    browser_url,
    normalise_served_host,
)
from server.routes import register_socket_events, routes


def create_app(
    engine: GameEngine, *, served_host: str = DEFAULT_SERVED_HOST
) -> tuple[Flask, SocketIO]:
    """Serve ``engine`` over HTTP and Socket.IO at ``served_host``; starts no thread."""
    app = Flask(__name__, root_path=str(PROJECT_ROOT), static_folder="static")
    app.extensions[ENGINE_EXTENSION] = engine
    # Werkzeug refuses a larger body with 413 before reading it.
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
    app.register_blueprint(routes)
    # No CORS headers on the routes and Socket.IO's default origin check: only pages
    # served by this server connect.
    socketio = SocketIO(app, async_mode="threading")
    register_socket_events(socketio, engine)
    # Outermost, after SocketIO wrapped wsgi_app: the Host check covers /socket.io too.
    app.wsgi_app = HostAllowlistMiddleware(  # type: ignore[method-assign]
        app.wsgi_app, allowed_hosts(served_host)
    )
    return app, socketio


def main() -> None:
    # Before the adapters: TTSEngine reads its API key from the environment.
    load_dotenv(PROJECT_ROOT / ".env")
    # Before any side effect: a G4AL_HOST no browser can reach exits here.
    host = served_host_from_environment()

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    # api/tts.py plays the voice lines through the mixer.
    pygame.mixer.init()

    use_pipeline_sinks()
    pipeline_logger = PipelineLogger()
    pipeline_logger.start_session()
    interpreter = MistralOrderInterpreter.from_api_key(
        os.environ.get("MISTRAL_API_KEY", ""), pipeline_logger=pipeline_logger
    )
    speaker = TTSEngine(pipeline_logger=pipeline_logger)
    engine = GameEngine(
        text_interpreter=interpreter, voice_interpreter=interpreter, speaker=speaker
    )
    interpreter.register_roster(engine.npcs)
    app, socketio = create_app(engine, served_host=host)

    game_thread = threading.Thread(target=engine.run_loop, args=(socketio,), daemon=True)
    game_thread.start()

    print(f"\n  G4AL Web UI → {browser_url(host)}\n")
    try:
        socketio.run(
            app,
            host=host,
            port=SERVER_PORT,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True,
        )
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        speaker.close()
        pipeline_logger.close()


def served_host_from_environment() -> str:
    """`G4AL_HOST`, normalised; exits with the reason when no browser could reach it."""
    try:
        return normalise_served_host(os.environ.get("G4AL_HOST", ""))
    except UnsupportedServedHostError as error:
        raise SystemExit(str(error)) from error
