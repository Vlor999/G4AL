"""Size of every object kind on the grid: footprint, height and drawn sprite box.

Units are tiles (``TILE_SIZE`` pixels). The values come from the sprite inventory in
``docs/assets.md``; the height model is decided in
``docs/adr/0002-object-dimensions-and-height-model.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from game.constants import HEIGHT_STEP


class ObjectKind(StrEnum):
    """Every kind of object drawn on the map. Building kinds equal their ``building_type``."""

    TREE = "tree"
    ROCK = "rock"
    GOLD_ROCK = "gold_rock"
    WHEAT = "wheat"
    HOUSE1 = "house1"
    HOUSE2 = "house2"
    HOUSE3 = "house3"
    CASTLE = "castle"
    BARRACKS = "barracks"
    ARCHERY = "archery"
    TOWER = "tower"
    MONASTERY = "monastery"
    STORAGE_HUT = "storage_hut"
    PAWN = "pawn"
    ARCHER = "archer"
    WILD_ARCHER = "wild_archer"
    SHEEP = "sheep"
    CAT = "cat"


@dataclass(frozen=True)
class SpriteBox:
    """Rectangle the sprite is drawn in, in tiles.

    ``anchor_x`` and ``anchor_y`` locate the ground point inside the box, measured from
    its top-left corner: the bottom centre of the footprint for an object on the grid,
    the feet (``x``, ``y``) for an NPC or a creature.
    """

    width: float
    height: float
    anchor_x: float
    anchor_y: float

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"sprite box must have a positive size, got {self}")


@dataclass(frozen=True)
class ObjectDimensions:
    """Footprint on the grid (whole tiles, width along columns, depth along rows), height
    in tiles above the footprint, and the box its sprite is drawn in."""

    footprint_width: int
    footprint_depth: int
    height: float
    sprite: SpriteBox

    def __post_init__(self) -> None:
        if self.footprint_width < 1 or self.footprint_depth < 1:
            raise ValueError(f"footprint must cover at least one tile, got {self}")
        if self.height < 0 or (self.height / HEIGHT_STEP) % 1:
            raise ValueError(f"height must be a non-negative multiple of {HEIGHT_STEP}: {self}")


def _building(width: int, depth: int, *, height: float) -> ObjectDimensions:
    # Every building is drawn with the house sprite stretched to its footprint width,
    # 1.5 times as tall as wide, standing on the bottom edge of its footprint.
    sprite_height = width * 1.5
    return ObjectDimensions(
        width, depth, height, SpriteBox(width, sprite_height, width / 2, sprite_height)
    )


OBJECT_DIMENSIONS: dict[ObjectKind, ObjectDimensions] = {
    ObjectKind.TREE: ObjectDimensions(1, 1, 1, SpriteBox(2.0, 2.6, 1.0, 2.6)),
    ObjectKind.ROCK: ObjectDimensions(1, 1, 0, SpriteBox(0.8, 0.8, 0.4, 0.9)),
    ObjectKind.GOLD_ROCK: ObjectDimensions(1, 1, 0, SpriteBox(1.0, 1.0, 0.5, 1.0)),
    ObjectKind.WHEAT: ObjectDimensions(1, 1, 0, SpriteBox(1.0, 1.0, 0.5, 1.0)),
    ObjectKind.HOUSE1: _building(2, 2, height=1),
    ObjectKind.HOUSE2: _building(2, 2, height=1),
    ObjectKind.HOUSE3: _building(2, 2, height=1),
    ObjectKind.CASTLE: _building(5, 3, height=1),
    ObjectKind.BARRACKS: _building(3, 3, height=1),
    ObjectKind.ARCHERY: _building(3, 3, height=1),
    ObjectKind.TOWER: _building(2, 2, height=2),
    ObjectKind.MONASTERY: _building(3, 3, height=2),
    ObjectKind.STORAGE_HUT: _building(2, 2, height=1),
    ObjectKind.PAWN: ObjectDimensions(1, 1, 0.5, SpriteBox(1.0, 1.0, 0.5, 0.84375)),
    ObjectKind.ARCHER: ObjectDimensions(1, 1, 0.5, SpriteBox(1.0, 1.0, 0.5, 0.84375)),
    ObjectKind.WILD_ARCHER: ObjectDimensions(1, 1, 0.5, SpriteBox(1.0, 1.0, 0.5, 0.84375)),
    ObjectKind.SHEEP: ObjectDimensions(1, 1, 0.5, SpriteBox(0.75, 0.75, 0.375, 0.5625)),
    ObjectKind.CAT: ObjectDimensions(1, 1, 0.5, SpriteBox(1.25, 1.25, 0.625, 1.0)),
}


BUILDING_KINDS = frozenset(
    {
        ObjectKind.HOUSE1,
        ObjectKind.HOUSE2,
        ObjectKind.HOUSE3,
        ObjectKind.CASTLE,
        ObjectKind.BARRACKS,
        ObjectKind.ARCHERY,
        ObjectKind.TOWER,
        ObjectKind.MONASTERY,
        ObjectKind.STORAGE_HUT,
    }
)


def find_building_dimensions(building_type: str) -> ObjectDimensions:
    """Dimensions of a building type; any other value gets the dimensions of ``house1``."""
    kind = next((kind for kind in BUILDING_KINDS if kind == building_type), ObjectKind.HOUSE1)
    return OBJECT_DIMENSIONS[kind]
