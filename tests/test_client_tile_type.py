import re
from pathlib import Path

from game.world.terrain import TileType

MAP_IMAGE_SCRIPT = Path(__file__).resolve().parents[1] / "static" / "map_image.js"
TILE_TYPE_BLOCK = re.compile(r"const TILE_TYPE = \{([^}]*)\};")
TILE_TYPE_ENTRY = re.compile(r"(\w+): (\d+)")


def test_the_client_tile_codes_match_the_server_tile_types() -> None:
    block = TILE_TYPE_BLOCK.search(MAP_IMAGE_SCRIPT.read_text(encoding="utf-8"))

    assert block is not None
    client_tile_types = {name: int(code) for name, code in TILE_TYPE_ENTRY.findall(block.group(1))}
    assert client_tile_types == {tile_type.name: tile_type.value for tile_type in TileType}
