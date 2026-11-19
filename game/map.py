"""Tile map the NPCs walk on, and the look-ups they use."""

from __future__ import annotations

import random

from game.map_generation import generate_terrain
from game.settings import MAP_COLS, MAP_ROWS, TILE_SIZE
from game.terrain import WALKABLE_TILES


class GameMap:
    """Grid of tiles, each with a ``TileType`` and a ``Biome``.

    ``rng`` is the random source the terrain was generated with; spawning draws from
    it next, so one seed replays the same map, resources and creatures. Without
    ``rng``, one is built from ``seed`` (a fresh one when ``seed`` is None).
    """

    def __init__(
        self,
        cols: int = MAP_COLS,
        rows: int = MAP_ROWS,
        seed: int | None = None,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self.cols = cols
        self.rows = rows
        self.rng = rng if rng is not None else random.Random(seed)
        terrain = generate_terrain(self.rng, cols=cols, rows=rows)
        self.tiles = terrain.tiles
        self.biomes = terrain.biomes

    def contains_tile(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    def is_walkable(self, col: int, row: int) -> bool:
        return self.contains_tile(col, row) and self.tiles[row][col] in WALKABLE_TILES

    def tile_center(self, col: int, row: int) -> tuple[float, float]:
        """Return the world-pixel center of a tile."""
        return col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2

    def world_to_tile(self, x: float, y: float) -> tuple[int, int]:
        """Convert world pixel coords → (col, row)."""
        return int(x // TILE_SIZE), int(y // TILE_SIZE)
