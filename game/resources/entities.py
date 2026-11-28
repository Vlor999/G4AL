"""Map objects the NPCs work on: trees, rocks, structures and wheat fields."""

from __future__ import annotations

from collections.abc import Collection
from typing import TYPE_CHECKING

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
from game.world.dimensions import (
    OBJECT_DIMENSIONS,
    ObjectDimensions,
    ObjectKind,
    find_building_dimensions,
)

if TYPE_CHECKING:
    from game.world.map import GameMap


class Resource:
    """A map object anchored at the tile (``col``, ``row``), its top-left corner."""

    kind: str = "resource"

    def __init__(self, col: int, row: int, hp: int, yields: dict[str, int]) -> None:
        self.col = col
        self.row = row
        self.hp = hp
        self.max_hp = hp
        self.depleted = False
        self.reserved_by: int | None = None  # id of the NPC that claimed it
        self.remaining_yields: dict[str, int] = dict(yields)
        self._total_units: int = sum(yields.values())

    @property
    def dimensions(self) -> ObjectDimensions:
        return OBJECT_DIMENSIONS[ObjectKind(self.kind)]

    @property
    def occupied_tiles(self) -> list[tuple[int, int]]:
        """Every tile the object covers: its anchor tile, or the whole footprint of a
        structure."""
        return [(self.col, self.row)]

    def collect_one_unit(self) -> tuple[str, int] | None:
        """Take one unit: ``(resource_type, 1)``, or None when nothing remains. Lowers
        ``hp`` in proportion and sets ``depleted`` once the last unit is taken."""
        for res_type in list(self.remaining_yields.keys()):
            if self.remaining_yields[res_type] > 0:
                self.remaining_yields[res_type] -= 1
                total_left = sum(self.remaining_yields.values())
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
    """A building the pawns raise: ``built`` once ``build_progress`` reaches 100."""

    kind = "structure"

    def __init__(
        self,
        col: int,
        row: int,
        build_progress: int = 0,
        building_type: str = "house1",
    ) -> None:
        super().__init__(col, row, hp=100, yields={})
        self.build_progress = build_progress
        self.built = False
        self.building_type = building_type

    @property
    def dimensions(self) -> ObjectDimensions:
        return find_building_dimensions(self.building_type)

    @property
    def occupied_tiles(self) -> list[tuple[int, int]]:
        tiles: list[tuple[int, int]] = []
        for dc in range(self.dimensions.footprint_width):
            for dr in range(self.dimensions.footprint_depth):
                tiles.append((self.col + dc, self.row + dr))
        return tiles

    def build_tick(self) -> None:
        self.build_progress = min(100, self.build_progress + 1)
        if self.build_progress >= 100:
            self.built = True


class WheatField(Resource):
    """A field a pawn plants: it grows one frame at a time and is harvested once
    ``fully_grown``."""

    kind = "wheat"

    def __init__(self, col: int, row: int) -> None:
        super().__init__(col, row, hp=10, yields={"wheat": WHEAT_YIELD})
        self.growth = 0  # frames, up to WHEAT_GROW_TIME
        self.fully_grown = False

    @property
    def growth_ratio(self) -> float:
        return min(1.0, self.growth / WHEAT_GROW_TIME)

    def grow_tick(self) -> None:
        """Grow by one frame; nothing happens once depleted or fully grown."""
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
