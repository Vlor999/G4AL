"""The tile names of static/tileset.js and the table scripts/tileset_reference.py writes."""

import pytest

from scripts.tileset_reference import (
    DOCUMENT_FILE,
    TABLE_END,
    TABLE_START,
    Tileset,
    TilesetTile,
    count_sheet_cells,
    label_reference_cells,
    parse_tileset,
    read_tileset,
    render_tile_table,
    replace_tile_table,
)

EMPTY_CELLS = {4, 13, 22, 31, 37, 38, 40, 46, 47, 49}


def test_every_non_empty_cell_of_the_sheet_has_one_name() -> None:
    tileset = read_tileset()

    indices = [tile.index for tile in tileset.tiles]
    assert (tileset.column_count, tileset.tile_size) == (9, 64)
    assert len(indices) == 44
    assert len(set(indices)) == 44
    assert set(indices) | EMPTY_CELLS == set(range(54))


def test_read_tileset_keeps_the_guide_id_and_the_note_of_an_entry() -> None:
    tiles = {tile.name: tile for tile in read_tileset().tiles}

    assert tiles["FLAT_CENTER"] == TilesetTile("FLAT_CENTER", 10, "FG5", "")
    assert tiles["RAMP_LEFT_BOTTOM"].guide_id == "ST29"
    assert tiles["RAMP_LEFT_BOTTOM"].note.startswith("Landing cell")


def test_parse_tileset_names_the_line_that_is_not_an_entry() -> None:
    source = (
        "const TILESET_TILE = Object.freeze({\n"
        "    FLAT_TOP_LEFT: 0, // FG1\n"
        "\n"
        "    FLAT_TOP: 1,\n"
        "});\n"
        "const TILESET_COLUMN_COUNT = 9;\n"
        "const TILESET_TILE_SIZE = 64;\n"
    )

    with pytest.raises(ValueError, match="FLAT_TOP: 1,"):
        parse_tileset(source)


def test_the_table_has_a_row_per_cell_with_its_column_and_row() -> None:
    tiles = [TilesetTile("FLAT_TOP_LEFT", 0, "FG1", ""), TilesetTile("ISLAND", 3, "FG16", "Alone.")]

    rows = render_tile_table(tiles, column_count=2, cell_count=4).splitlines()

    assert rows[2:] == [
        "| 0 | 0 | 0 | `FLAT_TOP_LEFT` | FG1 |  |",
        "| 1 | 1 | 0 | empty | - |  |",
        "| 2 | 0 | 1 | empty | - |  |",
        "| 3 | 1 | 1 | `ISLAND` | FG16 | Alone. |",
    ]


def test_the_sheet_has_54_cells_and_a_sheet_of_another_width_is_refused() -> None:
    tileset = read_tileset()

    assert count_sheet_cells(tileset, sheet_size=(576, 384)) == 54
    with pytest.raises(ValueError, match="columns"):
        count_sheet_cells(tileset, sheet_size=(512, 384))


def test_reference_cells_are_scaled_and_mark_the_empty_ones() -> None:
    tileset = Tileset(column_count=2, tile_size=64, tiles=[TilesetTile("A", 0, "FG1", "")])

    cells = label_reference_cells(tileset, cell_count=3)

    assert [(cell.left, cell.top, cell.size, cell.label) for cell in cells] == [
        (0, 0, 128, "0"),
        (128, 0, 128, "1 empty"),
        (0, 128, 128, "2 empty"),
    ]


def test_replace_tile_table_rewrites_only_the_text_between_the_markers() -> None:
    document = f"intro\n{TABLE_START}\nold\n{TABLE_END}\noutro\n"

    replaced = replace_tile_table(document, "new")

    assert replaced == f"intro\n{TABLE_START}\nnew\n{TABLE_END}\noutro\n"
    assert replace_tile_table(replaced, "new") == replaced


def test_replace_tile_table_refuses_a_document_without_the_markers() -> None:
    with pytest.raises(ValueError, match="markers"):
        replace_tile_table("no markers here", "new")


def test_a_pipe_in_a_note_is_escaped_in_the_table() -> None:
    tiles = [TilesetTile("FLAT_TOP_LEFT", 0, "FG1", "Water | land.")]

    rows = render_tile_table(tiles, column_count=1, cell_count=1).splitlines()

    assert rows[2] == "| 0 | 0 | 0 | `FLAT_TOP_LEFT` | FG1 | Water \\| land. |"


def test_the_committed_document_holds_the_table_of_the_current_tileset() -> None:
    tileset = read_tileset()
    document = DOCUMENT_FILE.read_text(encoding="utf-8")
    committed_table = document.split(TABLE_START + "\n")[1].split("\n" + TABLE_END)[0]

    expected = render_tile_table(
        tileset.tiles, column_count=tileset.column_count, cell_count=tileset.column_count * 6
    )
    assert committed_table == expected
