---
type: reference
title: Domain model
description: The game/ simulation, sub-package by sub-package - the NPC action machine, how a player order becomes an action, harvesting and the storage-full rule, resources and storage, orders and their outcome values, chat values, spawning and the world clock.
tags: [domain, npc, orders, storage, resources, spawning]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T16:09:17.330Z
sources:
  - id: openwiki-source-bfb818f4a0eb4aef9472705b
    resource: repo://game/npcs/actions.py
  - id: openwiki-source-9c5f07eead8172e6e31963a7
    resource: repo://game/npcs/npc_base.py
  - id: openwiki-source-d8e2a674e0b59daf6372e80a
    resource: repo://game/npcs/npc.py
  - id: openwiki-source-46a12a4841927745353b96bf
    resource: repo://game/orders/direct_orders.py
  - id: openwiki-source-89e94a5f3c0caa39f467f254
    resource: repo://game/orders/orders.py
  - id: openwiki-source-e8ce2b5dce076fe275be5b38
    resource: repo://game/resources/storage.py
  - id: openwiki-source-5712b0541b5af89e006f4ba3
    resource: repo://game/settings.py
  - id: openwiki-source-9a049830ee6d0ec18662aeea
    resource: repo://game/simulation.py
  - id: openwiki-source-56bbbe1245e7c4236d9f98cc
    resource: repo://game/spawning.py
  - id: openwiki-source-8d729023f6d263fa63206a02
    resource: repo://game/world/clock.py
  - id: openwiki-source-6aa90484abb0e3508c2f0a36
    resource: repo://game/world/map.py
  - id: openwiki-source-2bb4f9456b7b530d91f7448d
    resource: repo://game/world/terrain.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# Domain model

`game/` is the simulation. It does no I/O and imports only the standard library and itself, in sub-packages that depend downward (see [System overview](../architecture/system-overview.md)). Everything below advances one frame at a time when `game.simulation.advance_world` calls `update()` on each object; see [Game loop and state push](../workflows/game-loop-and-state-push.md).

| Sub-package | Modules |
|---|---|
| `game/orders/` | `orders.py` (voice and typed orders), `direct_orders.py` (mouse and buttons), `chat.py` |
| `game/npcs/` | `actions.py`, `npc_base.py`, `npc.py` (pawn), `archer.py` |
| `game/fauna/` | `fauna.py`, `sheep.py`, `cat.py`, `wild_archer.py`, `fauna_spawning.py`; see [Fauna, wild archers and combat](fauna-and-combat.md) |
| `game/combat/` | `arrows.py`, `targeting.py` |
| `game/resources/` | `entities.py`, `storage.py` |
| `game/world/` | `map.py`, `map_generation.py`, `terrain.py`, `pathfinding.py`, `dimensions.py`, `npc_names.py`, `clock.py`; see [World and map generation](world-and-map-generation.md) and [Pathfinding](pathfinding.md) |
| root | `spawning.py`, `simulation.py`, `ports.py`, `settings.py` (tuning), `constants.py` |

## Map

`GameMap` is a grid of `TileType` values (grass, dirt, sand, water), each tile also in a `Biome`. Grass, dirt and sand are walkable; water is not. The 30 by 20 map of 64-pixel tiles is generated from a seed; the engine builds it with seed 42, and the same `rng` drives spawning, names and fauna behaviour. `contains_tile`, `is_walkable`, `tile_center` and `world_to_tile` are the queries used by everything else. Generation is on [World and map generation](world-and-map-generation.md).

## NPCs and the action machine

`NPCBase` (`game/npcs/npc_base.py`) holds what every playable NPC shares: health, hunger, speed, an action queue (a `deque` of `Action`), the current action, a path, the carrying state and a speech bubble. `NPC` (kind `pawn`) subclasses it and implements `_next_action`, `_on_arrival` and `_perform`. `Archer` (kind `archer`) subclasses `NPC` and overrides those hooks with its combat behaviour.

- **States.** `State` is `IDLE`, `MOVING`, `PERFORMING`, `RETURNING`, `WAITING_DEPOSIT` or `DONE`. `update()` drains needs, then looks up one step per state in `_STEP_BY_STATE`: idle NPCs pop the next queued action, moving and returning ones follow their path, performing ones run the action, waiting ones retry the deposit, and `DONE` releases the resource reservation and starts the next queued action or goes idle.
- **Allowed actions.** `enqueue` refuses an action outside the NPC's `allowed_actions`: the NPC says "I can't do that!" and `enqueue` returns `False`. Pawns may chop wood, mine rock, build, move, eat, plant wheat and collect wheat; archers may move, shoot, defend and eat (`PAWN_ACTIONS`, `ARCHER_ACTIONS` in `game/npcs/actions.py`).
- **From order to action.** `create_order_action` is the one rule that turns a player order into an `Action`, shared by voice, typed and direct orders. `build` and `plant_wheat` aim at the order's target tile, or the NPC's own tile without one; `move_to` aims at the target; the other actions take no target.
- **Hunger.** Hunger drains every frame; at zero the NPC loses health each frame. Eating costs `EAT_WHEAT_COST` wheat from storage.
- **Harvest loop.** A pawn harvests one unit per `NPC_COLLECT_UNIT_TIME` frames, then walks to the storage hut and deposits. With an empty queue it returns to the same target until it is depleted.
- **Storage full.** At the hut, the load goes into storage as far as it fits and what does not fit stays carried. While any load is left, or when storage is full after the deposit and the queue is empty, the NPC says "Storage full!" and enters `WAITING_DEPOSIT`. It retries every frame once storage has room. `give_up_waiting_deposit` drops the load and goes idle; the engine calls it on every NPC for `/api/dismiss_storage`.
- **Reservations.** A harvest target records `reserved_by` with the NPC id so two NPCs do not claim the same resource; it is released when the action ends.
- **Building.** A new `house1` needs a free 2 by 2 footprint within `NPC_BUILD_SEARCH_RADIUS` tiles of the target, otherwise "No space to build!". It then spends `BUILD_COST_WOOD` (5) and `BUILD_COST_STONE` (3), or says "Not enough resources to build!". The NPC builds it from an adjacent tile at one percent per `NPC_BUILD_TIME / 100` frames; a finished house registers itself with storage.
- **Planting.** `plant_wheat` places a `WheatField` on the nearest free walkable tile within `NPC_PLANT_SEARCH_RADIUS`, otherwise "No space to plant!".

[Fauna, wild archers and combat](fauna-and-combat.md) covers the archer's combat actions.

## Resources and structures

`Resource` (`game/resources/entities.py`) is the base of `Tree`, `Rock` (stone, plus gold when `has_gold`), `Structure` (a multi-tile building with `build_progress` and `built`) and `WheatField` (grows over `WHEAT_GROW_TIME` frames, ticked by `advance_world`). Each resource tracks remaining yield per unit and is marked `depleted` at zero. Its `dimensions` and `occupied_tiles` come from the object dimension table.

## Storage

`ResourceStorage` is one global stockpile of wood, stone, gold and wheat. Capacity is `STORAGE_BASE_CAPACITY` (50) plus `HOUSE_CAPACITY_BONUS` (20) per completed house. `add` stores only what fits and returns the amount stored; `spend` returns `False` when stock is short; `discard_resources` removes up to the requested amounts and reports what it removed. `snapshot()` is the payload the client reads. The stored kinds live in `game/constants.py` as `STORED_RESOURCE_KINDS`.

## Orders

Two kinds of order reach NPCs, both returning an outcome value rather than raising:

- `game/orders/orders.py`: `NpcOrder` (from a voice or typed command, interpreted by an LLM) and `apply_orders`, which enqueues one action per order, shows the voice line as a speech bubble for `ORDER_SPEECH_DURATION_FRAMES` (360) when accepted, and returns an `OrderOutcome` with `is_accepted` and `is_spoken`. At most `TTS_MAX_SPEAKERS` (1) accepted orders per command are spoken aloud. Unknown NPC ids are not accepted. An `NpcOrder` can only carry one of `VOICE_ORDER_ACTIONS` (every action but `move_to`, which needs a target tile); building one with `move_to` raises `ValueError`. `CommandRefused` with a `RefusalReason` stands for a whole refused command. See [Voice and typed order flow](../workflows/voice-order-flow.md).
- `game/orders/direct_orders.py`: `DirectOrder` (mouse or button) and `apply_direct_order`, with outcomes `ACCEPTED`, `REFUSED_BY_NPC`, `UNKNOWN_NPC` and `TARGET_OUTSIDE_MAP`. A `move_to` without a target is rejected when the order is built.

`game/orders/chat.py` holds the values of the chat panel: `TypedCommand(text)`, `SpokenCommand()` (no text: the interpreter hears the audio) and `NpcVoiceLine(npc_name, voice_line)`.

## Spawning and the world clock

`spawn_world` (`game/spawning.py`) builds the initial `SpawnedWorld` from `game_map.rng`: a built storage hut at a fixed tile, resources by biome around it, three pawns near the map centre, two archers on rings around the hut, six sheep and a cat, and three wild archers in a camp in the bottom-right corner. It then links archers to the shared fauna and arrow lists, and wild archers to the NPC and arrow lists and the world clock. Those lists and the clock are shared by reference, so they are mutated in place.

`WorldClock` (`game/world/clock.py`) counts the frames completed since the start of the game. Only `advance` moves it, and `advance_world` calls it last in each frame, so during the n-th frame it reads n - 1. Wild archers read it for their start-of-game grace period.

## Names and settings

`NamePools` gives pawns, archers and wild archers names from their own pools, each drawn from the map's `rng` and recycled when exhausted. All tuning numbers (speeds, durations in frames at 60 FPS, costs, yields, spawn counts, biome densities) live in `game/settings.py`; other literals go in `game/constants.py`.
