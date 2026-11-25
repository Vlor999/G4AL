"""Procedural terrain of a new map: biome regions, lakes, dirt patches, fords.

Every random draw comes from the ``random.Random`` passed in, so one seed always gives
the same terrain (``docs/adr/0003-biome-map-generation.md``).
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass

from game.settings import (
    BIOME_BORDER_JITTER,
    BIOME_EDGE_MARGIN,
    BIOME_REGION_COUNTS,
    DIRT_PATCH_COUNTS,
    DIRT_PATCH_RADIUS_RANGE,
    HOME_MEADOW_RADIUS,
    LAKE_COUNT,
    LAKE_RADIUS_RANGE,
    LAKE_SHORE_WIDTH,
)
from game.world.terrain import WALKABLE_TILES, Biome, TileType

Tile = tuple[int, int]
NEIGHBOUR_STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class Terrain:
    """Ground of a map, indexed ``[row][col]``."""

    tiles: list[list[TileType]]
    biomes: list[list[Biome]]

    @property
    def cols(self) -> int:
        return len(self.tiles[0])

    @property
    def rows(self) -> int:
        return len(self.tiles)

    def all_tiles(self) -> list[Tile]:
        return [(col, row) for row in range(self.rows) for col in range(self.cols)]

    def contains(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    def is_walkable(self, col: int, row: int) -> bool:
        return self.contains(col, row) and self.tiles[row][col] in WALKABLE_TILES


def generate_terrain(rng: random.Random, *, cols: int, rows: int) -> Terrain:
    """Biome regions around a meadow at the map centre, then lakes and dirt patches.

    Every walkable tile is reachable from the centre: water that cuts a piece of land
    off becomes a sand ford.
    """
    home = (cols // 2, rows // 2)
    terrain = Terrain(
        tiles=[[TileType.GRASS] * cols for _ in range(rows)],
        biomes=_assign_biome_regions(rng, cols=cols, rows=rows, home=home),
    )
    _add_lakes(rng, terrain, home=home)
    _add_dirt_patches(rng, terrain)
    _open_fords(terrain, home=home)
    return terrain


def _squared_distance(first: Tile, second: Tile) -> int:
    return (first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2


def _inner_tiles(cols: int, rows: int) -> list[Tile]:
    col_margin = min(BIOME_EDGE_MARGIN, (cols - 1) // 2)
    row_margin = min(BIOME_EDGE_MARGIN, (rows - 1) // 2)
    return [
        (col, row)
        for row in range(row_margin, rows - row_margin)
        for col in range(col_margin, cols - col_margin)
    ]


def _assign_biome_regions(
    rng: random.Random, *, cols: int, rows: int, home: Tile
) -> list[list[Biome]]:
    """Voronoi regions: each tile takes the biome of its nearest seed, with jitter."""
    inner = _inner_tiles(cols, rows)
    seeds = [(home, Biome.MEADOW)]
    for biome, count in BIOME_REGION_COUNTS.items():
        seeds.extend((rng.choice(inner), biome) for _ in range(count))
    home_radius_squared = HOME_MEADOW_RADIUS**2
    biomes: list[list[Biome]] = []
    for row in range(rows):
        biome_row: list[Biome] = []
        for col in range(cols):
            if _squared_distance((col, row), home) <= home_radius_squared:
                biome_row.append(Biome.MEADOW)
                continue
            distances = [
                (_squared_distance((col, row), seed) + rng.random() * BIOME_BORDER_JITTER, biome)
                for seed, biome in seeds
            ]
            biome_row.append(min(distances, key=lambda pair: pair[0])[1])
        biomes.append(biome_row)
    return biomes


def _add_lakes(rng: random.Random, terrain: Terrain, *, home: Tile) -> None:
    for _ in range(LAKE_COUNT):
        radius = rng.randint(*LAKE_RADIUS_RANGE)
        outer_radius = radius + LAKE_SHORE_WIDTH
        keep_out = (HOME_MEADOW_RADIUS + outer_radius + 1) ** 2
        centres = [
            tile
            for tile in _inner_tiles(terrain.cols, terrain.rows)
            if _squared_distance(tile, home) > keep_out
        ]
        if centres:
            _stamp_lake(terrain, centre=rng.choice(centres), radius=radius)


def _stamp_lake(terrain: Terrain, *, centre: Tile, radius: int) -> None:
    outer_radius = radius + LAKE_SHORE_WIDTH
    for col, row in terrain.all_tiles():
        distance = _squared_distance((col, row), centre)
        if distance > outer_radius**2:
            continue
        terrain.biomes[row][col] = Biome.LAKE
        if distance <= radius**2:
            terrain.tiles[row][col] = TileType.WATER
        elif terrain.tiles[row][col] != TileType.WATER:
            terrain.tiles[row][col] = TileType.SAND


def _add_dirt_patches(rng: random.Random, terrain: Terrain) -> None:
    for biome, count in DIRT_PATCH_COUNTS.items():
        for _ in range(count):
            grass = [
                (col, row)
                for col, row in terrain.all_tiles()
                if terrain.biomes[row][col] == biome and terrain.tiles[row][col] == TileType.GRASS
            ]
            if not grass:
                break
            centre = rng.choice(grass)
            radius_squared = rng.randint(*DIRT_PATCH_RADIUS_RANGE) ** 2
            for col, row in grass:
                if _squared_distance((col, row), centre) <= radius_squared:
                    terrain.tiles[row][col] = TileType.DIRT


def _open_fords(terrain: Terrain, *, home: Tile) -> None:
    """Turn into sand the water on the shortest way from each cut-off piece of land home."""
    reachable = _reachable_from(terrain, home)
    while True:
        cut_off = next(
            (
                tile
                for tile in terrain.all_tiles()
                if terrain.is_walkable(*tile) and tile not in reachable
            ),
            None,
        )
        if cut_off is None:
            return
        for col, row in _shortest_way(terrain, start=cut_off, goals=reachable):
            if terrain.tiles[row][col] == TileType.WATER:
                terrain.tiles[row][col] = TileType.SAND
        reachable = _reachable_from(terrain, home)


def _reachable_from(terrain: Terrain, start: Tile) -> set[Tile]:
    reached = {start}
    queue = deque([start])
    while queue:
        col, row = queue.popleft()
        for step_col, step_row in NEIGHBOUR_STEPS:
            neighbour = (col + step_col, row + step_row)
            if neighbour not in reached and terrain.is_walkable(*neighbour):
                reached.add(neighbour)
                queue.append(neighbour)
    return reached


def _shortest_way(terrain: Terrain, *, start: Tile, goals: set[Tile]) -> list[Tile]:
    """Tiles from ``start`` to the nearest goal, crossing any terrain."""
    came_from: dict[Tile, Tile | None] = {start: None}
    queue = deque([start])
    while queue:
        tile = queue.popleft()
        if tile in goals:
            way: list[Tile] = []
            step: Tile | None = tile
            while step is not None:
                way.append(step)
                step = came_from[step]
            return way
        for step_col, step_row in NEIGHBOUR_STEPS:
            neighbour = (tile[0] + step_col, tile[1] + step_row)
            if neighbour not in came_from and terrain.contains(*neighbour):
                came_from[neighbour] = tile
                queue.append(neighbour)
    return []
