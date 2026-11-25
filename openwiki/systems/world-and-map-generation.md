---
type: system
title: World and map generation
description: How a new map is generated from one seed - biome regions, lakes, dirt patches and fords - how biomes drive where resources and sheep appear, how object sizes and heights are defined, and how NPC names are drawn.
tags: [map, terrain, biomes, dimensions, domain]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T16:09:17.330Z
sources:
  - id: openwiki-source-09da166315e69a49f3933fb7
    resource: repo://game/constants.py
  - id: openwiki-source-60dda682a1a9c84439a10909
    resource: repo://game/fauna/fauna_spawning.py
  - id: openwiki-source-f17691beea254cf11ea5bd78
    resource: repo://game/resources/entities.py
  - id: openwiki-source-5712b0541b5af89e006f4ba3
    resource: repo://game/settings.py
  - id: openwiki-source-574f4b5d9621debb4cef0cd6
    resource: repo://game/world/dimensions.py
  - id: openwiki-source-fedc70db983abddcdcbc9b2a
    resource: repo://game/world/map_generation.py
  - id: openwiki-source-6aa90484abb0e3508c2f0a36
    resource: repo://game/world/map.py
  - id: openwiki-source-504d98e9d76a9ce2845e13ba
    resource: repo://game/world/npc_names.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# World and map generation

`game/world/` is the bottom layer of the domain: it imports nothing from the other game sub-packages. It holds the map, its generation, terrain types, object dimensions, name pools, pathfinding and the world clock. Pathfinding has its own page ([Pathfinding](pathfinding.md)); the clock is on [Domain model](domain-model.md).

## One seed, one game

`GameMap(cols, rows, seed, *, rng)` (`game/world/map.py`) builds a `random.Random` from `seed`, or takes one, and keeps it as `rng`. The terrain, spawning, NPC names (`name_pools`) and fauna behaviour all draw from it, so one seed replays the same game. The engine uses seed 42 on a 30 by 20 map of 64-pixel tiles (`MAP_COLS`, `MAP_ROWS`, `TILE_SIZE`).

Each tile has a `TileType` (grass, dirt, sand, water; all but water are walkable) and a `Biome` (meadow, forest, highland, lake), both indexed `[row][col]`.

## Terrain generation (`game/world/map_generation.py`)

`generate_terrain(rng, *, cols, rows)` runs four steps (ADR `docs/adr/0003-biome-map-generation.md`):

1. **Biome regions.** A Voronoi split: a meadow seed at the map centre plus random seeds per biome (`BIOME_REGION_COUNTS`), kept `BIOME_EDGE_MARGIN` tiles from the edge. Each tile takes the biome of its nearest seed, with random jitter on the distance (`BIOME_BORDER_JITTER`) for ragged borders. Tiles within `HOME_MEADOW_RADIUS` of the centre always stay meadow.
2. **Lakes.** `LAKE_COUNT` lakes, each a disc of water of radius in `LAKE_RADIUS_RANGE` with a sand shore of `LAKE_SHORE_WIDTH`, all marked as lake biome. Lake centres keep clear of the home meadow.
3. **Dirt patches.** Per biome (`DIRT_PATCH_COUNTS`), small discs of grass in that biome turn to dirt.
4. **Fords.** Every walkable tile must be reachable from the centre. For each cut-off piece of land, the water on the shortest way home turns to sand.

## What grows and lives where

- `spawn_resources` (`game/resources/entities.py`) rolls each free walkable tile inside the map border against its biome's `TREE_DENSITY` and `ROCK_DENSITY`. A rock holds gold with the biome's `GOLD_ROCK_SHARE`. Forests are dense with trees, highlands with rocks and gold; lakes grow nothing. The storage hut's tiles are reserved.
- Sheep spawn on free grass in a `SHEEP_BIOMES` biome (meadow) when one is left, else on any free grass (`game/fauna/fauna_spawning.py`).
- The client draws each biome with its own ground tileset and decorations (`static/map_image.js`), from the `biomes` grid in the state. See [Browser client](browser-client.md).

## Object dimensions (`game/world/dimensions.py`)

`OBJECT_DIMENSIONS` holds one `ObjectDimensions` per `ObjectKind`: the footprint in whole tiles (width along columns, depth along rows), the height in tiles, and the `SpriteBox` the sprite is drawn in, with its ground anchor (ADR `docs/adr/0002-object-dimensions-and-height-model.md`, values from `docs/assets.md`).

- **Height unit.** Heights count in half tiles (`HEIGHT_STEP` in `game/constants.py`). A height that is negative or not a multiple of 0.5 raises at construction, as does a footprint under one tile or a sprite box without positive size.
- **Buildings.** House 2 by 2 and 1 high, tower 2 by 2 and 2 high, castle 5 by 3. Every building uses the house sprite stretched to its footprint width.
- **Other kinds.** Trees, rocks, wheat, NPCs and fauna cover one tile; trees are 1 high, NPCs and fauna 0.5, rocks and wheat 0.
- **Lookup.** `find_building_dimensions` gives a building type's dimensions, falling back to `house1`.

Resources read their `dimensions` and `occupied_tiles` from this table, pawns use it to find a free footprint for a new house, and the serializer sends `footprint`, `height` and `sprite` for every resource, NPC and creature, so the client decides no size. See [Game loop and state push](../workflows/game-loop-and-state-push.md).

## Names (`game/world/npc_names.py`)

`NamePools` holds one `NamePool` each for pawns (`NPCName`: Bob, Paul, Thomas, Marie, Sam, Lisa), archers and wild archers. A pool draws a name from the map's `rng` that is not in use yet, and recycles the whole pool once exhausted. Pawn names match the personalities and voices of `api/roster.py`. See [Adapters](adapters.md).

## Tests

`tests/test_map.py`, `tests/test_map_generation.py`, `tests/test_dimensions.py`, `tests/test_entities.py` and `tests/test_npc_names.py` cover these modules. Domain tests that need a hand-drawn map use the `build_map` fixture, which overrides the generated tiles with ASCII rows and sets every biome to meadow. See [Testing and quality gates](../testing/quality-gates-and-tests.md).
