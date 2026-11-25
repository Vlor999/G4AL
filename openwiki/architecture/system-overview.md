---
type: architecture
title: System overview and layers
description: How G4AL splits into a pure game domain in layered sub-packages, vendor adapters, a server entry point and a browser client, which ports join them and which threads run at runtime.
tags: [architecture, layers, ports, threading, import-contract]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T15:38:15.273Z
sources:
  - id: openwiki-source-68f8bb6dd19f483ad1ca049d
    resource: repo://docs/adr/0004-game-sub-packages.md
  - id: openwiki-source-7b58b9d865554d4c161a99ca
    resource: repo://game/ports.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-141c86ea716204370c1b7a2d
    resource: repo://server/app.py
  - id: openwiki-source-0d5ad3511dcf5d6f5ad53c00
    resource: repo://server/engine.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# System overview and layers

G4AL is a 2D survival game controlled by voice or typed commands. A Flask and Socket.IO server runs the simulation and a browser Canvas client draws it. Four layers keep that split clean.

| Layer | Path | Role |
|---|---|---|
| Domain | `game/` | Pure simulation: map, NPCs, fauna, combat, resources, storage, orders, pathfinding, tuning. See [Domain model](../systems/domain-model.md). |
| Adapters | `api/` | One module per outside system: Mistral (text and Voxtral audio), ElevenLabs plus the pygame mixer, log files, plus the model catalog. See [Adapters](../systems/adapters.md). |
| Entry point | `server/`, `main.py` | Builds the adapters, owns the game loop thread and the selected model, maps HTTP and Socket.IO to domain calls. |
| Client | `static/` | Rendering, input, push-to-talk, chat panel. See [Browser client](../systems/browser-client.md). |

## Dependency direction

The domain imports no adapter, no entry point and no I/O library. Two `lint-imports` contracts in `pyproject.toml` enforce it, `TYPE_CHECKING` imports included:

- **Forbidden imports.** `game` may not import `api`, `server`, `main`, `flask`, `flask_socketio`, `mistralai`, `elevenlabs`, `pygame`, `loguru` or `dotenv`.
- **Downward layers.** Inside `game/`, a sub-package imports only the ones below it (ADR `docs/adr/0004-game-sub-packages.md`):

| Layer, top to bottom | Holds |
|---|---|
| `game.spawning`, `game.simulation`, `game.ports` | World setup, one simulation frame, the ports |
| `game.orders` | Voice and direct orders, chat values |
| `game.npcs` and `game.fauna` (one shared layer) | Pawns, archers, the action machine; sheep, cat, wild archers |
| `game.combat` | Arrows and targeting |
| `game.resources` | Trees, rocks, structures, wheat, storage |
| `game.world` | Map, terrain generation, pathfinding, dimensions, names, `WorldClock` |

`npcs` and `fauna` share a layer because archers and wild archers name each other's types. `game/settings.py` and `game/constants.py` sit outside the layers; every package reads them. Sub-packages have empty `__init__.py` files and no re-exports, so imports name the module (`from game.world.map import GameMap`). [Testing and quality gates](../testing/quality-gates-and-tests.md) lists where the contracts run.

## Ports and injection

What the domain needs from outside is declared as three `Protocol` classes in `game/ports.py`:

- `TextOrderInterpreter.interpret_text(command, *, model_id)` returns a list of `NpcOrder` or a `CommandRefused`. Every LLM provider implements it.
- `VoiceOrderInterpreter.interpret_voice(audio, *, model_id)` does the same for a WAV recording. Only a provider with speech input implements it.
- Both raise only `OrderInterpretationError` when the service fails, and both block, so they never run on the game loop thread.
- `VoiceLineSpeaker.speak(voice_line, npc_name)` only queues the line. A line that cannot be voiced is dropped by the adapter, so this port has no error type.

Ports are named after capabilities and their methods after game actions, not vendor calls. `GameEngine` takes `model_selection`, `speaker` and an optional `run_in_background` as keyword-only constructor arguments. The interpreters reach it inside a `ModelSelection` (see [LLM models and providers](../systems/llm-models-and-providers.md)). Tests pass fakes (`tests/fakes.py`) and a `run_now` runner, and never patch module globals.

## Composition root

`server/app.py` is the only place that wires things together:

- `create_app(engine, *, served_host)` builds the Flask app and the Socket.IO server around an engine and starts no thread. The engine is stored in `app.extensions` under a constant key. The outermost WSGI layer is `HostAllowlistMiddleware`, so the `Host` check also covers `/socket.io`. See [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md).
- `main()` loads `.env`, then validates the environment before any side effect: `G4AL_HOST` (a zone id exits) and the startup model with its provider key (`read_startup_models`, which exits on an unknown provider or model or a missing key). It then sets `SDL_VIDEODRIVER=dummy`, initialises pygame and its mixer, installs the log sinks, builds one `PipelineLogger` and the `TTSEngine`, and calls `build_engine`.
- `build_engine` builds the interpreters of every provider whose key is set, wraps them in a `ModelSelection`, creates the `GameEngine` and registers the new world's NPC roster with each provider's interpreters.
- `main()` then starts the loop thread and serves on port 8000 of the normalised `G4AL_HOST` (default `127.0.0.1`), printing the URL a browser should open.

Importing these modules starts no vendor client, loop, audio device or log sink.

## Threads at runtime

- The **game loop thread** runs `GameEngine.run_loop` at 60 FPS. Each tick calls `game.simulation.advance_world`. See [Game loop and state push](../workflows/game-loop-and-state-push.md).
- Each command, typed or spoken, is interpreted on a **background daemon thread** started by the engine's `run_in_background`. See [Voice and typed order flow](../workflows/voice-order-flow.md).
- `TTSEngine` has one **daemon worker thread** that drains a FIFO queue, so voice lines never overlap.
- Flask and Socket.IO handlers run on Werkzeug threads (`async_mode="threading"`) and reach the game only through `GameEngine` methods, which take its lock. `ModelSelection` has its own lock.

## Related pages

- [Quickstart](../quickstart.md)
- [World and map generation](../systems/world-and-map-generation.md)
- [Running and configuration](../operations/running-and-configuration.md)
