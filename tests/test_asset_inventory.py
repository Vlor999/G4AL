"""The parts of scripts/asset_inventory.py that need no image library."""

import pytest

from scripts.asset_inventory import (
    SpriteMeasure,
    find_frame_count,
    format_row,
    group_by_feature,
    read_frame_counts,
    read_loaded_paths,
    render,
    render_unused,
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


def test_loaded_paths_include_the_images_style_css_references() -> None:
    assert "UI Elements/UI Elements/Cursors/Cursor_01.png" in read_loaded_paths()


@pytest.mark.parametrize(
    ("unused", "expected_lines"),
    [
        ([], ["None."]),
        (
            ["Units/Blue Units/Lancer/Lancer_Idle.png"],
            ["### Future unit type: lancer", "- `Units/Blue Units/Lancer/Lancer_Idle.png`"],
        ),
        (["Elsewhere/Thing.png"], ["### No intended feature recorded"]),
    ],
)
def test_unused_pngs_are_grouped_under_a_heading_by_intended_feature(
    unused: list[str], expected_lines: list[str]
) -> None:
    assert all(line in render_unused(unused) for line in expected_lines)


def test_group_by_feature_puts_a_path_under_the_first_matching_prefix() -> None:
    groups = group_by_feature(
        ["Terrain/Resources/Tools/Tool_01.png", "Terrain/Resources/Wood/Wood Resource/W.png"]
    )
    assert list(groups.values()) == [
        ["Terrain/Resources/Tools/Tool_01.png"],
        ["Terrain/Resources/Wood/Wood Resource/W.png"],
    ]


def test_a_tilemap_row_links_to_the_tile_index_and_other_rows_do_not() -> None:
    tilemap = SpriteMeasure("Terrain/Tileset/Tilemap_color3.png", 576, 384, 1, (0, 0, 576, 384))
    shadow = SpriteMeasure("Terrain/Tileset/Shadow.png", 192, 192, 1, None)

    assert format_row(tilemap).startswith(
        "| `Terrain/Tileset/Tilemap_color3.png` ([tile index](tileset.md)) | 576×384 |"
    )
    assert format_row(shadow).startswith("| `Terrain/Tileset/Shadow.png` | 192×192 |")
