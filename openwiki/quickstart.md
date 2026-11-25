---
type: guide
title: G4AL quickstart
description: What G4AL is, how to run and verify it, and a task-to-page map of this wiki.
tags: [quickstart, overview, onboarding]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T15:38:15.273Z
sources:
  - id: openwiki-source-7b58b9d865554d4c161a99ca
    resource: repo://game/ports.py
  - id: openwiki-source-833e692518af9eeaf8564cc6
    resource: repo://main.py
  - id: openwiki-source-012f2c78e3b1446dfc35803f
    resource: repo://Makefile
  - id: openwiki-source-141c86ea716204370c1b7a2d
    resource: repo://server/app.py
  - id: openwiki-source-0d5ad3511dcf5d6f5ad53c00
    resource: repo://server/engine.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# G4AL quickstart

G4AL is a top-down 2D survival game controlled by voice or typed commands. The player holds a key and speaks an order, or types it in the chat panel. A Mistral model turns it into structured NPC orders: Voxtral hears the audio, and the player can switch to a text-only model in game. The NPCs carry the orders out (chop wood, mine rock, build, farm, defend) and answer with an ElevenLabs voice line. A Flask and Socket.IO server runs the simulation at 60 FPS and pushes the state to an HTML5 Canvas client about 20 times a second.

## Run and verify

```bash
make install   # uv sync + pre-commit hooks
cp .env.example .env   # add MISTRAL_API_KEY, optionally ELEVENLABS_API_KEY
make run       # http://localhost:8000
make check     # format, lint + import contracts, mypy strict, vulture, pytest + coverage
```

Python 3.11 and `uv` only. `make check` is the verification for a change; do not start the server to verify one. The server exits at startup when the start model's provider key is missing. Details: [Running and configuration](operations/running-and-configuration.md) and [Testing and quality gates](testing/quality-gates-and-tests.md).

## Layers in one glance

| Path | Role |
|---|---|
| `game/` | Pure simulation, no I/O, in sub-packages that import downward (`orders`, `npcs` and `fauna`, `combat`, `resources`, `world`) |
| `api/` | Adapters for Mistral, ElevenLabs and logging, the shared order contract and the model catalog |
| `server/` | Entry point: engine, routes, Host allowlist, model selection, serialization |
| `static/` | Browser client, classic scripts |

Dependencies point inward and are injected through three ports: a text order interpreter, a voice order interpreter and a voice line speaker. See [System overview](architecture/system-overview.md).

## Where to look

| If you want to... | Read |
|---|---|
| Understand how a spoken or typed order becomes an action | [Voice and typed order flow](workflows/voice-order-flow.md) |
| Add a model or an LLM provider, or change the model picker | [LLM models and providers](systems/llm-models-and-providers.md) |
| Change the tick, the push rate or the state payload | [Game loop and state push](workflows/game-loop-and-state-push.md) |
| Add or change an NPC action, resource, building or storage rule | [Domain model](systems/domain-model.md) |
| Change the terrain, biomes, object sizes or names | [World and map generation](systems/world-and-map-generation.md) |
| Change enemies, arrows or archer behaviour | [Fauna, wild archers and combat](systems/fauna-and-combat.md) |
| Change how units find their way | [Pathfinding](systems/pathfinding.md) |
| Add or change a route, a body or a check | [HTTP and Socket.IO contract](systems/http-and-socketio-contract.md) |
| Change the Mistral or ElevenLabs integration, or logs | [Adapters](systems/adapters.md) |
| Change rendering, input, chat or push-to-talk | [Browser client](systems/browser-client.md) |

## Rules worth knowing first

- The game loop runs in its own thread; routes and handlers change state only through `GameEngine`.
- Durations and speeds in `game/settings.py` are in frames at 60 FPS, not seconds.
- A `game` sub-package imports only the ones below it; `lint-imports` fails otherwise.
- Without `ELEVENLABS_API_KEY` NPCs do not speak and nothing fails.
- Outside data is parsed once, at the boundary, into domain types: an LLM answer in the order contract, a request body in the route.
