---
type: "Reference"
title: "Domain model"
openwiki_generated: true
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:41:00.050Z
sources:
  - id: openwiki-source-b6bdd063bb51ed4cad8f56bc
    resource: repo://game/actions.py
  - id: openwiki-source-487fb4d406cec828c3ee91a7
    resource: repo://game/direct_orders.py
  - id: openwiki-source-29c073a53cd50a764c314a0b
    resource: repo://game/map.py
  - id: openwiki-source-aea888e2ae6044f79c756acd
    resource: repo://game/npc_base.py
  - id: openwiki-source-a0dada0f8ccf133763481458
    resource: repo://game/npc.py
  - id: openwiki-source-d31645d2375ae8305792ee37
    resource: repo://game/orders.py
  - id: openwiki-source-56bbbe1245e7c4236d9f98cc
    resource: repo://game/spawning.py
  - id: openwiki-source-d3bc9333b7576b7f246a5eaa
    resource: repo://game/storage.py
generated: { by: "claude-code", at: "2026-11-18T09:41:00.050Z" }
---


# Domain model

`game/` is the simulation. It does no I/O and imports only the standard library and itself (see [System overview](../architecture/system-overview.md)). Everything below advances one frame at a time when `GameEngine.tick` calls `update()` on each object.

## Map

`GameMap` is a grid of `TileType` values (grass, dirt, sand, water). Grass, dirt and sand are walkable. The 30 by 20 map of 64-pixel tiles is generated procedurally from a seed with dirt patches and ponds; the engine builds it with seed 42. `contains_tile`, `is_walkable`, `tile_center` and `world_to_tile` are the queries used by everything else. Pathfinding is on its own page: [Pathfinding](pathfinding.md).

## NPCs and the action machine

`NPCBase` (`game/npc_base.py`) holds what every playable NPC shares: health, hunger, speed, an action queue (a `deque` of `Action`), the current action, a path, and the carrying state. `NPC` (kind `pawn`) subclasses it and implements `_next_action`, `_on_arrival` and `_perform`. `Archer` (kind `archer`) subclasses `NPC` and overrides those hooks with its combat behaviour.

- **States.** `State` is `IDLE`, `MOVING`, `PERFORMING`, `RETURNING`, `WAITING_DEPOSIT` or `DONE`. `update()` dispatches on the state each frame: idle NPCs pop the next queued action, moving ones follow their path, performing ones run the action timer, and `DONE` releases the resource reservation and starts the next queued action or goes idle.
- **Allowed actions.** `enqueue` refuses an action outside the NPC's `allowed_actions`: the NPC says "I can't do that!" and `enqueue` returns `False`. Pawns may chop wood, mine rock, build, move, eat, plant wheat and collect wheat; archers may move, shoot, defend and eat (`PAWN_ACTIONS`, `ARCHER_ACTIONS` in `game/actions.py`). The `collect_wheat` enum member is lowercase in source, with value `collect_wheat`.
- **Hunger.** Hunger drains every frame; at zero the NPC loses health each frame. Eating costs wheat from storage.
- **Harvest loop.** A pawn harvests one unit per `NPC_COLLECT_UNIT_TIME` frames, then walks to the storage hut and deposits. If it had a harvest in progress and the queue is empty, it automatically returns to the same target until it is depleted. If storage is full it says "Storage full!" and enters `WAITING_DEPOSIT`; `give_up_waiting_deposit` drops the load and goes idle.
- **Reservations.** A harvest target records `reserved_by` with the NPC id so two NPCs do not claim the same resource; it is released when the action ends.
- **Building.** A build spends 5 wood and 3 stone from storage when placing a new `house1`, then the NPC builds it adjacent at one percent per `NPC_BUILD_TIME / 100` frames; a finished house registers itself with storage.

[Fauna, wild archers and combat](fauna-and-combat.md) covers the archer's combat actions.

## Resources and structures

`Resource` is the base of `Tree`, `Rock` (stone, plus gold when `has_gold`), `Structure` (a multi-tile building with `build_progress` and `built`) and `WheatField` (grows over `WHEAT_GROW_TIME` frames, ticked by the engine). Each resource tracks remaining yield per unit and is marked `depleted` at zero.

## Storage

`ResourceStorage` is one global stockpile of wood, stone, gold and wheat. Capacity is a base of 50 plus 20 per completed house. `add` stores only what fits and returns the amount stored; `spend` returns `False` when stock is short; `discard_resources` removes up to the requested amounts and reports what it removed. `snapshot()` is the payload the client reads. The stored kinds live in `game/constants.py` as `STORED_RESOURCE_KINDS`.

## Orders

Two kinds of order reach NPCs, both returning an outcome value rather than raising:

- `game/orders.py`: `NpcOrder` (from a voice command) and `apply_orders`, which enqueues one action per order and returns an `OrderOutcome` with `is_accepted` and `is_spoken`. At most `TTS_MAX_SPEAKERS` (1) accepted orders per command are spoken aloud. Unknown NPC ids are not accepted. `CommandRefused` with a `RefusalReason` stands for a whole refused command. See [Voice order flow](../workflows/voice-order-flow.md).
- `game/direct_orders.py`: `DirectOrder` (mouse or button) and `apply_direct_order`, with outcomes `ACCEPTED`, `REFUSED_BY_NPC`, `UNKNOWN_NPC` and `TARGET_OUTSIDE_MAP`. A `move_to` without a target is rejected when the order is built. `build` and `plant_wheat` without a target use the NPC's own tile.

## Spawning

`spawn_world` builds the initial `SpawnedWorld`: random resources, a built storage hut at a fixed tile, three pawns near the map centre, two archers on rings around the hut, six sheep, a cat and three wild archers in the bottom-right corner. It then links archers and wild archers to the shared fauna, NPC and arrow lists. Those lists are shared by reference, so they are mutated in place.

## Names and settings

`NPCName` and `pick_npc_name` give each pawn a unique name from a six-name pool, recycling when exhausted; archers draw from their own list. All tuning numbers (speeds, durations in frames at 60 FPS, costs, yields, spawn counts) live in `game/settings.py`; other literals go in `game/constants.py`.
