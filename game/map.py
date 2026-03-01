"""Tile-based map with Clash-of-Clans style terrain generation."""

from __future__ import annotations

import random
from enum import IntEnum
from typing import List, Tuple, Optional

from game.settings import TILE_SIZE, MAP_COLS, MAP_ROWS


class TileType(IntEnum):
    GRASS = 0
    DIRT = 1
    SAND = 2
    WATER = 3


# Whether an NPC can walk on this tile
WALKABLE = {TileType.GRASS, TileType.DIRT, TileType.SAND}


class GameMap:
    """Grid of tiles + helper look-ups used by NPCs."""

    def __init__(
        self, cols: int = MAP_COLS, rows: int = MAP_ROWS, seed: int | None = None
    ):
        self.cols = cols
        self.rows = rows
        if seed is not None:
            random.seed(seed)
        self.tiles: List[List[TileType]] = self._generate()

    # ── generation ───────────────────────────────────────────────────────
    def _generate(self) -> List[List[TileType]]:
        """Simple procedural generation: mostly grass with ponds & dirt patches."""
        grid = [[TileType.GRASS for _ in range(self.cols)] for _ in range(self.rows)]

        # sprinkle some dirt patches (paths / bare ground)
        for _ in range(8):
            cx, cy = random.randint(2, self.cols - 3), random.randint(2, self.rows - 3)
            radius = random.randint(1, 3)
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.cols and 0 <= ny < self.rows:
                        if dx * dx + dy * dy <= radius * radius:
                            grid[ny][nx] = TileType.DIRT

        # a couple of small ponds (water only, no sand border)
        for _ in range(3):
            cx, cy = random.randint(3, self.cols - 4), random.randint(3, self.rows - 4)
            radius = random.randint(1, 2)
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.cols and 0 <= ny < self.rows:
                        if dx * dx + dy * dy <= radius * radius:
                            grid[ny][nx] = TileType.WATER
        return grid

    # ── queries ──────────────────────────────────────────────────────────
    def is_walkable(self, col: int, row: int) -> bool:
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.tiles[row][col] in WALKABLE
        return False

    def tile_center(self, col: int, row: int) -> Tuple[float, float]:
        """Return the world-pixel center of a tile."""
        return col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2

    def world_to_tile(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world pixel coords → (col, row)."""
        return int(x // TILE_SIZE), int(y // TILE_SIZE)

    def find_nearest_walkable(
        self, col: int, row: int, max_radius: int = 10
    ) -> Optional[Tuple[int, int]]:
        """BFS outward to find nearest walkable tile (used for placement fallback)."""
        from collections import deque

        visited = set()
        queue = deque()
        queue.append((col, row))
        visited.add((col, row))
        while queue:
            c, r = queue.popleft()
            if self.is_walkable(c, r):
                return (c, r)
            for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nc, nr = c + dc, r + dr
                if (
                    (nc, nr) not in visited
                    and 0 <= nc < self.cols
                    and 0 <= nr < self.rows
                ):
                    if abs(nc - col) <= max_radius and abs(nr - row) <= max_radius:
                        visited.add((nc, nr))
                        queue.append((nc, nr))
        return None
