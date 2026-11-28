---
type: workflow
title: Game loop and state push
description: How GameEngine advances the simulation at 60 FPS under one lock, in what order a frame updates the world, and how the state is serialised and pushed over Socket.IO every third tick.
tags: [game-loop, engine, socketio, threading, serialization]
sources:
  - id: openwiki-source-9a049830ee6d0ec18662aeea
    resource: repo://game/simulation.py
  - id: openwiki-source-0d5ad3511dcf5d6f5ad53c00
    resource: repo://server/engine.py
  - id: openwiki-source-ad8a0f8b85e961c2b13636c0
    resource: repo://server/serialization.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
verified:
  - by: openwiki/0.5.2
    at: 2026-11-28T10:49:24.445Z
---

# Game loop and state push

`GameEngine` (`server/engine.py`) owns the game state and the loop; one frame of the world is `game.simulation.advance_world`. The entry point starts `run_loop` in a daemon thread (see [System overview](../architecture/system-overview.md)).

## Concurrency

All mutable game state sits behind one `threading.Lock`. These all take it:

- `tick` and `get_state`;
- `give_direct_order`, `select_npc`, `deselect_all`, `discard_resources` and `release_npcs_waiting_deposit`;
- the start of a command (game log and chat) and the hand-over of its interpreter answer.

Routes and Socket.IO handlers mutate the game only through these methods, so the loop thread and request threads never touch NPCs concurrently. `select_model` goes to `ModelSelection`, which has its own lock. See [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md).

## One tick

`tick()` holds the lock, applies every pending interpreter answer in arrival order (see [Voice and typed order flow](voice-order-flow.md)), then calls `advance_world`, which in order:

1. Calls `update()` on every NPC, then every creature.
2. Calls `grow_tick()` on every `WheatField`.
3. Advances every arrow's `frame` and drops arrows whose frame reached `totalFrames`.
4. Removes fauna at zero health.
5. Removes dead NPCs. If the selected NPC died and NPCs remain, the first NPC becomes selected.
6. Advances the `WorldClock`.

The NPC, fauna and arrow lists are mutated in place (slice assignment), because archers and wild archers hold references to them. See [Fauna, wild archers and combat](../systems/fauna-and-combat.md).

## Loop timing

`run_loop` computes `1 / FPS` (`FPS = 60` in `game/settings.py`), runs `tick`, counts frames, and sleeps for the remainder of the frame. If a frame takes longer than its budget it does not sleep and does not skip ticks. Durations and speeds in settings are in frames, not seconds. `stop()` clears the running flag; the entry point closes the speaker and the pipeline logger.

## State push

Every third frame (`_ws_push_interval = 3`, about 20 Hz) the loop emits `state` with `get_state()` on namespace `/`. A new connection also receives `state` once on connect.

A push failure must not stop the game. The loop catches the exception, logs a single `state_push` warning at the start of a failure streak and a single info message when pushes recover, so a dropped client does not flood logs at 20 lines a second. `tests/e2e/test_game_loop.py` drives this with a fake socket that raises for the first pushes.

## Serialisation

`serialize_state` (`server/serialization.py`) builds the client JSON from the game state, with the lock held by the caller:

- `map` (cols, rows, tile size, tile ids, biome names);
- `resources` (non-depleted only, with kind-specific fields for rocks, structures and wheat fields);
- `npcs`, `fauna` and `arrows` (with a `progress` ratio);
- `storage` (a snapshot) and `storageFullAlert` (true when any NPC waits to deposit);
- `log` (the last 20 messages) and `chat` (typed commands, spoken commands and NPC voice lines, each with a `kind`);
- `models`, `selectedModelId` and `hasVoiceInput` for the model picker and push-to-talk.

Every resource, NPC and creature also carries its `footprint`, `height` and `sprite` box from the object dimension table (see [World and map generation](../systems/world-and-map-generation.md)). Numbers are rounded for compactness. NPC speech text is sent only while its timer runs.

The engine keeps up to 50 log messages and the serializer sends the latest 20; the chat keeps the last `CHAT_HISTORY_LENGTH` (30) messages. Game-domain logic stays out of serialization: it only reads state. The client turns this into a view; see [Browser client](../systems/browser-client.md).
