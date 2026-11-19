import pytest

from game.dimensions import (
    OBJECT_DIMENSIONS,
    ObjectDimensions,
    ObjectKind,
    SpriteBox,
    find_building_dimensions,
)
from game.settings import TILE_SIZE

TS = TILE_SIZE
Rect = tuple[float, float, float, float]

# Sprite rectangles (left, top, width, height) that static/renderer.js drew before the
# state carried dimensions, relative to its reference point: the footprint centre for a
# resource, the feet for an NPC or a creature.
DRAWN_BEFORE: dict[ObjectKind, Rect] = {
    ObjectKind.TREE: (-TS * 2.0 / 2, -TS * 2.6 + TS * 0.5, TS * 2.0, TS * 2.6),
    ObjectKind.GOLD_ROCK: (-TS * 1.0 / 2, -TS * 1.0 / 2, TS * 1.0, TS * 1.0),
    ObjectKind.ROCK: (-TS * 0.8 / 2, -TS * 0.8 / 2, TS * 0.8, TS * 0.8),
    ObjectKind.PAWN: (-32, -64 + 10, 64, 64),
    ObjectKind.ARCHER: (-32, -64 + 10, 64, 64),
    ObjectKind.WILD_ARCHER: (-32, -64 + 10, 64, 64),
    ObjectKind.SHEEP: (-24, -48 + 12, 48, 48),
    ObjectKind.CAT: (-40, -80 + 16, 80, 80),
}
UNIT_KINDS = {
    ObjectKind.PAWN,
    ObjectKind.ARCHER,
    ObjectKind.WILD_ARCHER,
    ObjectKind.SHEEP,
    ObjectKind.CAT,
}
GRID_SIZES_BEFORE = {
    "house1": (2, 2),
    "house2": (2, 2),
    "house3": (2, 2),
    "castle": (5, 3),
    "barracks": (3, 3),
    "archery": (3, 3),
    "tower": (2, 2),
    "monastery": (3, 3),
    "storage_hut": (2, 2),
    "unknown": (2, 2),
}


def drawn_now(dimensions: ObjectDimensions, *, is_on_grid: bool) -> Rect:
    """The rectangle renderer.js spriteRect() computes, relative to the same reference."""
    ground_y = dimensions.footprint_depth * TS / 2 if is_on_grid else 0
    box = dimensions.sprite
    return (-box.anchor_x * TS, ground_y - box.anchor_y * TS, box.width * TS, box.height * TS)


def house_drawn_before(width: int, depth: int) -> Rect:
    drawn_width = width * TS
    drawn_height = drawn_width * 1.5
    return (-drawn_width / 2, depth * TS / 2 - drawn_height, drawn_width, drawn_height)


@pytest.mark.parametrize("kind", list(DRAWN_BEFORE))
def test_sprite_box_draws_the_rectangle_the_renderer_hard_coded(kind: ObjectKind) -> None:
    rect = drawn_now(OBJECT_DIMENSIONS[kind], is_on_grid=kind not in UNIT_KINDS)
    assert rect == pytest.approx(DRAWN_BEFORE[kind])


@pytest.mark.parametrize(("building_type", "footprint"), list(GRID_SIZES_BEFORE.items()))
def test_building_keeps_its_footprint_and_house_sprite_rectangle(
    building_type: str, footprint: tuple[int, int]
) -> None:
    dimensions = find_building_dimensions(building_type)
    assert (dimensions.footprint_width, dimensions.footprint_depth) == footprint
    assert drawn_now(dimensions, is_on_grid=True) == pytest.approx(house_drawn_before(*footprint))


def test_every_object_kind_has_dimensions() -> None:
    assert set(OBJECT_DIMENSIONS) == set(ObjectKind)


def test_a_kind_that_is_not_a_building_gets_house_dimensions() -> None:
    assert find_building_dimensions("tree") == OBJECT_DIMENSIONS[ObjectKind.HOUSE1]


@pytest.mark.parametrize(
    ("footprint_width", "footprint_depth", "height"),
    [(0, 1, 1), (1, 0, 1), (1, 1, -0.5), (1, 1, 0.3)],
)
def test_invalid_dimensions_are_refused(
    footprint_width: int, footprint_depth: int, height: float
) -> None:
    with pytest.raises(ValueError, match=r"footprint|height"):
        ObjectDimensions(footprint_width, footprint_depth, height, SpriteBox(1, 1, 0.5, 1))


def test_a_sprite_box_without_area_is_refused() -> None:
    with pytest.raises(ValueError, match="positive size"):
        SpriteBox(0, 1, 0, 0)
