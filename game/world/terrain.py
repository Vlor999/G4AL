"""Ground types of a map tile: its terrain and the biome it belongs to."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class TileType(IntEnum):
    GRASS = 0
    DIRT = 1
    SAND = 2
    WATER = 3


WALKABLE_TILES = frozenset({TileType.GRASS, TileType.DIRT, TileType.SAND})


class Biome(StrEnum):
    """Region of the map; it sets the ground drawn and what grows or lives there
    (``docs/adr/0003-biome-map-generation.md``)."""

    MEADOW = "meadow"
    FOREST = "forest"
    HIGHLAND = "highland"
    LAKE = "lake"
