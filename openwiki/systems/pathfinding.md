---
type: system
title: Pathfinding
description: How NPCs and fauna find paths on the tile grid with A*, how blocked tiles and unwalkable goals are handled, how free tiles near an order are found, and how a path is followed frame by frame.
tags: [pathfinding, a-star, movement, domain]
sources:
  - id: openwiki-source-72a55b5222417e6181ee13d0
    resource: repo://game/fauna/fauna.py
  - id: openwiki-source-9c5f07eead8172e6e31963a7
    resource: repo://game/npcs/npc_base.py
  - id: openwiki-source-d8e2a674e0b59daf6372e80a
    resource: repo://game/npcs/npc.py
  - id: openwiki-source-f17691beea254cf11ea5bd78
    resource: repo://game/resources/entities.py
  - id: openwiki-source-739fe961f17d5ba86aa05c6c
    resource: repo://game/world/pathfinding.py
generated: { by: "claude-code", at: "2026-11-25T16:09:17.330Z" }
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T16:09:17.330Z
---

# Pathfinding

Movement on the tile grid uses A* with a Manhattan heuristic and four-way moves. Two A* implementations exist, one for player NPCs and one for fauna, plus a breadth-first search for free tiles. All belong to the [Domain model](domain-model.md), in `game/world/pathfinding.py` and `game/fauna/fauna.py`.

## `find_path` (`game/world/pathfinding.py`)

`find_path(game_map, start, goal, blocked=None)` returns a list of `(col, row)` tiles from start to goal inclusive, or an empty list when no path exists.

- Neighbours are the four cardinal tiles that are walkable on the map. Water and out-of-map tiles are not.
- `blocked` is an optional set of tiles treated as impassable. The goal tile is never treated as blocked, so an NPC can still path toward a tile another object stands on.
- If the goal itself is not walkable, the first walkable neighbour among eight (cardinal then diagonal) becomes the goal; with none, the result is empty.

## `find_nearest_tile`

`find_nearest_tile(origin, *, max_radius, is_suitable)` searches breadth-first outward from `origin`, through every tile and not only walkable ones, for the nearest tile where `is_suitable` holds, within `max_radius` columns and rows. It returns `None` when none qualifies. Pawns use it to place a wheat field on a free tile (`NPC_PLANT_SEARCH_RADIUS`) and a house on a free footprint (`NPC_BUILD_SEARCH_RADIUS`).

## How NPCs use it

`NPCBase._plan_move_to` calls `find_path` with `blocked` set to every tile a non-depleted resource covers, read from `Resource.occupied_tiles`, so a structure blocks its whole footprint (`_occupied_by_structures`). An empty path sets the state to `DONE`, so an unreachable order ends rather than stalling. Otherwise the NPC enters `MOVING`.

`_follow_path` moves toward the next tile centre at the NPC's speed each frame, snaps to the centre when closer than one step, and advances the index. At the end of the path a `RETURNING` NPC deposits at the hut; any other state calls `_on_arrival`, which each subclass overrides.

The return trip to the hut targets the nearest walkable tile edge-adjacent to the hut footprint. When the NPC has no hut, no such tile exists or no path is found, it deposits where it stands.

## Combat ranges

Archers and wild archers do not path to their target's tile. `find_walkable_tile_in_range` (`game/combat/targeting.py`) picks the walkable tile within shooting range of the target that is nearest to the shooter, without checking reachability. The shooter then paths there. See [Fauna, wild archers and combat](fauna-and-combat.md).

## Fauna

`Fauna._simple_path` is a lighter A* with no blocked set: it ignores structures and other creatures, and returns an empty list when the goal is not walkable. `Fauna._follow_path` is the same step-toward-tile-centre logic. A creature with no path goes idle.

## Tests

`tests/test_pathfinding.py` builds small maps from ASCII rows with the `build_map` fixture and covers the basic path cases, a detour around blocked tiles, the goal never counting as blocked, and `find_nearest_tile`. See [Testing and quality gates](../testing/quality-gates-and-tests.md).
