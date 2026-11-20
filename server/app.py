"""Builds the Flask + Socket.IO app around a game engine and starts the server."""

from __future__ import annotations

import os
import threading

import pygame
from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO

from api.logger import PipelineLogger, use_pipeline_sinks
from api.tts import TTSEngine
from game.ports import VoiceLineSpeaker
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
from server.model_selection import ModelSelection
from server.providers import StartupModels, build_order_interpreters, read_startup_models
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
    # Likewise an unknown model, or one whose provider key is missing: no order could
    # ever be interpreted.
    startup_models = read_startup_models(os.environ)

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    # api/tts.py plays the voice lines through the mixer.
    pygame.mixer.init()

    use_pipeline_sinks()
    pipeline_logger = PipelineLogger()
    pipeline_logger.start_session()
    speaker = TTSEngine(pipeline_logger=pipeline_logger)
    engine = build_engine(startup_models, speaker=speaker, pipeline_logger=pipeline_logger)
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


def build_engine(
    startup_models: StartupModels, *, speaker: VoiceLineSpeaker, pipeline_logger: PipelineLogger
) -> GameEngine:
    """A game engine on the start model, with the interpreters of every provider whose
    key is set, each one knowing the NPCs of the new world."""
    interpreters = {
        provider: build_order_interpreters(
            provider, api_key=api_key, pipeline_logger=pipeline_logger
        )
        for provider, api_key in startup_models.api_keys.items()
    }
    model_selection = ModelSelection(
        available_models=startup_models.available_models,
        selected=startup_models.selected,
        interpreters=interpreters,
    )
    engine = GameEngine(model_selection=model_selection, speaker=speaker)
    for provider_interpreters in interpreters.values():
        provider_interpreters.register_roster(engine.npcs)
    return engine


def served_host_from_environment() -> str:
    """`G4AL_HOST`, normalised; exits with the reason when no browser could reach it."""
    try:
        return normalise_served_host(os.environ.get("G4AL_HOST", ""))
    except UnsupportedServedHostError as error:
        raise SystemExit(str(error)) from error
