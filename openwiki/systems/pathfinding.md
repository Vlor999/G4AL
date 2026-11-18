---
type: system
title: Pathfinding
description: How NPCs and fauna find paths on the tile grid with A*, how blocked tiles and unwalkable goals are handled, and how a path is followed frame by frame.
tags: [pathfinding, a-star, movement, domain]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:30:24.405Z
sources:
  - id: openwiki-source-1118e86fbc148d23a1bc4bc9
    resource: repo://game/creatures.py
  - id: openwiki-source-aea888e2ae6044f79c756acd
    resource: repo://game/npc_base.py
  - id: openwiki-source-4ed105ab120763d6a84c6a26
    resource: repo://game/pathfinding.py
generated: { by: "claude-code", at: "2026-11-18T09:30:24.405Z" }
---

# Pathfinding

Movement on the tile grid uses A* with a Manhattan heuristic and four-way moves. Two implementations exist, one for player NPCs and one for fauna. Both belong to the [Domain model](domain-model.md).

## `find_path` (`game/pathfinding.py`)

`find_path(game_map, start, goal, blocked=None)` returns a list of `(col, row)` tiles from start to goal inclusive, or an empty list when no path exists.

- Neighbours are the four cardinal tiles that are walkable on the map. Water and out-of-map tiles are not.
- `blocked` is an optional set of tiles treated as impassable. The goal tile is never treated as blocked, so an NPC can still path toward a tile another unit stands on.
- If the goal itself is not walkable, the first walkable neighbour among eight (cardinal then diagonal) becomes the goal; with none, the result is empty.

## How NPCs use it

`NPCBase._plan_move_to` calls `find_path` with `blocked` set to the tiles of every non-depleted resource and every tile of multi-tile structures (`_occupied_by_structures`). An empty path sets the state to `DONE`, so an unreachable order ends rather than stalling. Otherwise the NPC enters `MOVING`.

`_follow_path` moves toward the next tile centre at the NPC's speed each frame, snaps to the centre when closer than one step, and advances the index. At the end of the path a `RETURNING` NPC deposits at the hut; any other state calls `_on_arrival`, which each subclass overrides. The return trip to the hut targets the nearest walkable tile edge-adjacent to the hut footprint; when no path is found the NPC deposits where it stands. See [Fauna, wild archers and combat](fauna-and-combat.md) for archers walking to firing range.

## Fauna

`Fauna._simple_path` is a lighter A* with no blocked set: it assumes no NPC or resource collision avoidance and returns an empty list when the goal is not walkable. `Fauna._follow_path` is the same step-toward-tile-centre logic.

## Tests

`tests/test_pathfinding.py` builds small maps from ASCII rows with the `build_map` fixture and covers the basic path, a detour around blocked tiles and the goal never counting as blocked. See [Testing and quality gates](../testing/quality-gates-and-tests.md).
