---
type: architecture
title: System overview and layers
description: How G4AL splits into a pure game domain, vendor adapters, a server entry point and a browser client, and which threads run at runtime.
tags: [architecture, layers, ports, threading]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:41:00.050Z
sources:
  - id: openwiki-source-7b58b9d865554d4c161a99ca
    resource: repo://game/ports.py
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-141c86ea716204370c1b7a2d
    resource: repo://server/app.py
  - id: openwiki-source-0d5ad3511dcf5d6f5ad53c00
    resource: repo://server/engine.py
generated: { by: "claude-code", at: "2026-11-18T09:30:24.405Z" }
---

# System overview and layers

G4AL is a voice-controlled 2D survival game. A Flask and Socket.IO server runs the simulation and a browser Canvas client draws it. Four layers keep that split clean.

| Layer | Path | Role |
|---|---|---|
| Domain | `game/` | Pure simulation: map, NPCs, fauna, resources, storage, pathfinding, tuning. See [Domain model](../systems/domain-model.md). |
| Adapters | `api/` | One module per outside system: Mistral Voxtral, ElevenLabs plus the pygame mixer, log files. See [Adapters](../systems/adapters.md). |
| Entry point | `server/`, `main.py` | Builds the adapters, owns the game loop thread, maps HTTP and Socket.IO to domain calls. |
| Client | `static/` | Rendering, input, push-to-talk. See [Browser client](../systems/browser-client.md). |

## Dependency direction

The domain imports no adapter, no entry point and no I/O library. The `lint-imports` contract in `pyproject.toml` enforces it: `game` may not import `api`, `server`, `main`, `flask`, `flask_socketio`, `mistralai`, `elevenlabs`, `pygame`, `loguru` or `dotenv`. The contract also covers imports under `TYPE_CHECKING`. [Testing and quality gates](../testing/quality-gates-and-tests.md) lists where it runs.

## Ports and injection

What the domain needs from outside is declared as two `Protocol` classes in `game/ports.py`:

- `OrderInterpreter.interpret(audio)` returns a list of `NpcOrder` or a `CommandRefused`. It raises only `OrderInterpretationError` when the service fails.
- `VoiceLineSpeaker.speak(voice_line, npc_name)` only queues the line. A line that cannot be voiced is dropped by the adapter, so this port has no error type.

Ports are named after capabilities and their methods after game actions, not vendor calls. `GameEngine` takes both as keyword-only constructor arguments, so tests pass fakes (`tests/fakes.py`) and never patch module globals.

## Composition root

`server/app.py` is the only place that wires things together:

- `create_app(engine)` builds the Flask app and the Socket.IO server around an engine and starts no thread. The engine is stored in `app.extensions` under a constant key.
- `main()` loads `.env`, sets `SDL_VIDEODRIVER=dummy`, initialises pygame and its mixer, builds `VoxtralOrderInterpreter` and `TTSEngine`, injects them in `GameEngine`, registers the NPC roster with the interpreter, and starts the loop thread. It then serves on port 8000 of `G4AL_HOST` (default `127.0.0.1`).

Importing these modules starts no vendor client, loop or audio device.

## Threads at runtime

- The **game loop thread** runs `GameEngine.run_loop` at 60 FPS. See [Game loop and state push](../workflows/game-loop-and-state-push.md).
- Each voice command spawns a **worker thread** that blocks on the interpreter call. See [Voice order flow](../workflows/voice-order-flow.md).
- `TTSEngine` has one **daemon worker thread** that drains a FIFO queue, so voice lines never overlap.
- Flask and Socket.IO handlers run on Werkzeug threads (`async_mode="threading"`) and reach the game only through `GameEngine` methods, which take its lock.

## Related pages

- [Quickstart](../quickstart.md)
- [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md)
