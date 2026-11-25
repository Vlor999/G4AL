from collections.abc import Callable, Iterator
from typing import Any

import pytest
from loguru import logger

from api.logger import has_event
from game.clock import WorldClock
from game.map import GameMap
from game.terrain import Biome, TileType

_TILE_BY_SYMBOL = {
    ".": TileType.GRASS,
    ":": TileType.DIRT,
    "s": TileType.SAND,
    "~": TileType.WATER,
}

MapBuilder = Callable[[list[str]], GameMap]
LlmEndRecords = list[tuple[str, dict[str, Any]]]


def clock_at(elapsed_frames: int) -> WorldClock:
    """A world clock that has advanced *elapsed_frames* frames."""
    clock = WorldClock()
    for _ in range(elapsed_frames):
        clock.advance()
    return clock


@pytest.fixture
def build_map() -> MapBuilder:
    """Build a meadow GameMap whose tiles are drawn row by row with `_TILE_BY_SYMBOL`."""

    def build(rows: list[str]) -> GameMap:
        game_map = GameMap(seed=0)
        game_map.cols = len(rows[0])
        game_map.rows = len(rows)
        game_map.tiles = [[_TILE_BY_SYMBOL[symbol] for symbol in row] for row in rows]
        game_map.biomes = [[Biome.MEADOW] * len(row) for row in rows]
        return game_map

    return build


@pytest.fixture
def llm_end_records() -> Iterator[LlmEndRecords]:
    """The message and ``extra`` fields of every ``llm_end`` record the sinks keep."""
    records: LlmEndRecords = []
    handler_id = logger.add(
        lambda message: records.append((message.record["message"], message.record["extra"])),
        filter=lambda record: has_event(record) and record["extra"]["event"] == "llm_end",
    )
    yield records
    logger.remove(handler_id)
