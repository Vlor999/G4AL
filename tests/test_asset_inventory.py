"""The parts of scripts/asset_inventory.py that need no image library."""

from scripts.asset_inventory import (
    SpriteMeasure,
    find_frame_count,
    read_frame_counts,
    read_loaded_paths,
    render,
)

TREE = "Terrain/Resources/Wood/Trees/Tree1.png"
RED_ARCHER_IDLE = "Units/Red Units/Archer/Archer_Idle.png"


def test_frame_counts_come_from_details_js_and_red_units_reuse_the_blue_ones() -> None:
    frame_counts = read_frame_counts()
    assert frame_counts[TREE] == 8
    assert find_frame_count(frame_counts, RED_ARCHER_IDLE) == 6
    assert find_frame_count(frame_counts, "Terrain/Tileset/Shadow.png") == 1


def test_loaded_paths_include_the_sprites_js_template_frames() -> None:
    loaded = read_loaded_paths()
    assert {TREE, RED_ARCHER_IDLE, "lechat/frame_000.png", "lechat/frame_026.png"} <= loaded


def test_render_lists_game_sprites_with_their_dimensions_and_the_unused_ones() -> None:
    tree = SpriteMeasure(TREE, 1536, 256, 8, (37, 51, 156, 241))
    empty = SpriteMeasure("UI Elements/Blank.png", 64, 64, 1, None)

    page = render([tree, empty], unused=["Particle FX/Fire_03.png"], missing=[])

    assert "| 192×256 | (37, 51, 156, 241) | (96, 241) | 2.97 | tree 1×1 | 1 |" in page
    assert "| `UI Elements/Blank.png` | 64×64 | 1 | 64×64 | - | - | - | - | - |" in page
    assert "- `Particle FX/Fire_03.png`" in page
    assert page.split("## Referenced but missing on disk")[1].count("None.") == 1
