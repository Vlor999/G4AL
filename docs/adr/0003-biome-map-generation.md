# 0003. Biome map generation

## Context

`GameMap` filled the grid with grass, dirt patches and ponds, seeded the global
`random` module, and spread trees and rocks evenly. A forest or a quarry could not
exist, and a seed did not replay the map once anything else drew from `random`.

## Decision

- Four biomes (`Biome` in `game/terrain.py`); every tile carries one next to its
  `TileType`, and the state sends it (`map.biomes`, `docs/api.md`).

  | Biome | Ground (tileset of its grass) | Elevation range (ADR 0002 unit) | Walkable | Trees / rocks per free tile | Gold share of rocks | Fauna | Decorations |
  |---|---|---|---|---|---|---|---|
  | meadow | grass `Tilemap_color2`, dirt patches | 0 | yes | 0.02 / 0.01 | 0 | sheep | bushes, 1 tile in 30 |
  | forest | grass `Tilemap_color3` | 0 | yes | 0.3 / 0.01 | 0 | none | bushes, 1 tile in 8 |
  | highland | grass `Tilemap_color1`, many dirt patches | 0 to 1 | yes | 0.02 / 0.15 | 0.35 | none | none |
  | lake | water, sand shore and fords (`Tilemap_color5`) | 0 | water no, sand yes | 0 / 0 | 0 | none | rocks in the water |

  Dirt keeps `Tilemap_color4`. Elevation stays 0 everywhere until the floors ticket
  adds tile elevation; highland is the only biome allowed to rise, by up to one tile.
- **Generation method:** Voronoi regions on the default 30 × 20 map. A meadow seed sits
  at the map centre, and every tile within `HOME_MEADOW_RADIUS` of it is meadow without
  water, so the storage hut, the pawns and the archers spawn as before. Forest,
  highland and meadow seeds are drawn inside a margin; each tile takes the biome of its
  nearest seed, with a random jitter on the distances for ragged borders. Lakes are
  stamped afterwards (water disc, sand ring) away from home, then dirt patches inside
  each land biome. Last, any walkable tile that water cuts off from the centre gets a
  sand ford along its shortest way back, so every walkable tile is reachable from the
  storage hut.
- All randomness comes from one injected `random.Random`: `GameMap(rng=...)`, or
  `GameMap(seed=...)` which builds it. Spawning draws from the same `game_map.rng`, so
  one seed replays the map, the biomes, the resources and the creatures. The global
  `random` is no longer seeded.
- Resources are rolled per free walkable tile against the biome densities above; the
  storage hut footprint is kept free. Sheep spawn on free meadow grass; the wild archer
  camp and the cat keep their corners, whatever the biome. Wheat fields are
  not spawned: pawns plant them, wherever the player orders.
- Tuning numbers live in `game/settings.py`; the client maps biomes to tilesets and
  bushes (`static/map_image.js`), a view decision.

## Considered options

- Value noise (Perlin or simplex) with thresholds: smoother borders, but it needs a
  noise implementation in `game/` and gives less control over how many regions of each
  biome a small 30 × 20 map gets.
- Region growing from seeds: close to Voronoi, with more tuning knobs and more code.
- Removing cut-off land instead of opening fords: simpler, but it can swallow the wild
  archer camp corner.

## Consequences

The map seen with the server's seed 42 changes. Map generation no longer touches the
global `random`, so the seeded sequences other code draws from it shift (two fauna
tests were updated for that reason). NPC names and fauna behaviour still use the global
`random`.
