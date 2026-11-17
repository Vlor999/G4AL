from collections import Counter

from game.creatures import spawn_fauna
from tests.conftest import MapBuilder


def test_spawn_fauna_places_sheep_wild_archers_and_one_cat(build_map: MapBuilder) -> None:
    game_map = build_map(["." * 10] * 8)
    fauna = spawn_fauna(game_map, [], sheep_count=3, wild_archer_count=2)
    assert Counter(creature.kind for creature in fauna) == {
        "sheep": 3,
        "wild_archer": 2,
        "cat": 1,
    }
    tiles = [creature.tile_pos for creature in fauna]
    assert len(tiles) == len(set(tiles))
