"""Harvestable world entities: trees, rocks, and buildable structures."""

from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING

from game.dimensions import (
    OBJECT_DIMENSIONS,
    ObjectDimensions,
    ObjectKind,
    find_building_dimensions,
)
from game.settings import (
    GOLD_ROCK_SHARE,
    ROCK_DENSITY,
    ROCK_GOLD_YIELD,
    ROCK_STONE_YIELD,
    TREE_DENSITY,
    TREE_WOOD_YIELD,
    WHEAT_GROW_TIME,
    WHEAT_YIELD,
)

if TYPE_CHECKING:
    from game.map import GameMap


class Resource:
    """Base class for any harvestable map object sitting on a tile."""

    kind: str = "resource"

    def __init__(self, col: int, row: int, hp: int, yields: dict[str, int]) -> None:
        self.col = col
        self.row = row
        self.hp = hp
        self.max_hp = hp
        self.yields = yields  # {"wood": 10, …}
        self.depleted = False
        self.reserved_by: int | None = None  # NPC id that claimed this resource

        # Per-unit collection tracking
        self.remaining_yields: dict[str, int] = dict(yields)
        self._total_units: int = sum(yields.values())

    @property
    def dimensions(self) -> ObjectDimensions:
        return OBJECT_DIMENSIONS[ObjectKind(self.kind)]

    def collect_one_unit(self) -> tuple[str, int] | None:
        """Collect a single unit from this resource.

        Returns ``(resource_type, 1)`` or *None* if nothing remains.
        Marks the resource as depleted once all units are gone.
        """
        for res_type in list(self.remaining_yields.keys()):
            if self.remaining_yields[res_type] > 0:
                self.remaining_yields[res_type] -= 1
                total_left = sum(self.remaining_yields.values())
                # Update HP proportionally for visual feedback
                self.hp = max(0, round(self.max_hp * total_left / max(1, self._total_units)))
                if total_left <= 0:
                    self.depleted = True
                return (res_type, 1)
        self.depleted = True
        return None


class Tree(Resource):
    kind = "tree"

    def __init__(self, col: int, row: int) -> None:
        super().__init__(col, row, hp=TREE_WOOD_YIELD * 3, yields={"wood": TREE_WOOD_YIELD})


class Rock(Resource):
    kind = "rock"

    def __init__(self, col: int, row: int, has_gold: bool = False) -> None:
        yields = {"stone": ROCK_STONE_YIELD}
        if has_gold:
            yields["gold"] = ROCK_GOLD_YIELD
        super().__init__(col, row, hp=ROCK_STONE_YIELD * 4, yields=yields)
        self.has_gold = has_gold

    @property
    def dimensions(self) -> ObjectDimensions:
        return OBJECT_DIMENSIONS[ObjectKind.GOLD_ROCK if self.has_gold else ObjectKind.ROCK]


class Structure(Resource):
    """A player-built structure (e.g. storage hut). Placeholder for v1."""

    kind = "structure"

    def __init__(
        self,
        col: int,
        row: int,
        build_progress: int = 0,
        building_type: str = "house1",
    ) -> None:
        super().__init__(col, row, hp=100, yields={})
        self.build_progress = build_progress  # 0..100
        self.built = False
        self.building_type = building_type
        self.grid_width = self.dimensions.footprint_width
        self.grid_height = self.dimensions.footprint_depth

    @property
    def dimensions(self) -> ObjectDimensions:
        return find_building_dimensions(self.building_type)

    @property
    def occupied_tiles(self) -> list[tuple[int, int]]:
        """Return every (col, row) this structure covers."""
        tiles: list[tuple[int, int]] = []
        for dc in range(self.grid_width):
            for dr in range(self.grid_height):
                tiles.append((self.col + dc, self.row + dr))
        return tiles

    def build_tick(self) -> None:
        self.build_progress = min(100, self.build_progress + 1)
        if self.build_progress >= 100:
            self.built = True


class WheatField(Resource):
    """A plantable wheat field that grows over time and can be harvested."""

    kind = "wheat"

    def __init__(self, col: int, row: int) -> None:
        # Growth is tracked separately by self.growth.
        super().__init__(col, row, hp=10, yields={"wheat": WHEAT_YIELD})
        self.growth = 0  # 0..WHEAT_GROW_TIME
        self.fully_grown = False

    @property
    def growth_ratio(self) -> float:
        return min(1.0, self.growth / WHEAT_GROW_TIME)

    def grow_tick(self) -> None:
        """Call every frame. The field grows passively."""
        if self.depleted or self.fully_grown:
            return
        self.growth += 1
        if self.growth >= WHEAT_GROW_TIME:
            self.fully_grown = True


def spawn_resources(
    game_map: GameMap, *, reserved: Collection[tuple[int, int]] = ()
) -> list[Resource]:
    """Trees and rocks on the free walkable tiles inside the map border, each tile rolled
    against the densities of its biome with ``game_map.rng``. ``reserved`` tiles stay free."""
    resources: list[Resource] = []
    for row in range(1, game_map.rows - 1):
        for col in range(1, game_map.cols - 1):
            if not game_map.is_walkable(col, row) or (col, row) in reserved:
                continue
            resource = _roll_resource(game_map, (col, row))
            if resource is not None:
                resources.append(resource)
    return resources


def _roll_resource(game_map: GameMap, tile: tuple[int, int]) -> Resource | None:
    col, row = tile
    biome = game_map.biomes[row][col]
    roll = game_map.rng.random()
    if roll < TREE_DENSITY[biome]:
        return Tree(col, row)
    if roll < TREE_DENSITY[biome] + ROCK_DENSITY[biome]:
        return Rock(col, row, has_gold=game_map.rng.random() < GOLD_ROCK_SHARE[biome])
    return None
