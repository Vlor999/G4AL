from collections import Counter

from game.fauna_spawning import spawn_fauna
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


def test_spawn_fauna_places_wild_archers_near_the_map_edges(build_map: MapBuilder) -> None:
    game_map = build_map(["." * 20] * 20)

    fauna = spawn_fauna(game_map, [], sheep_count=0, wild_archer_count=40)

    edge_distances = [
        min(col, row, game_map.cols - 1 - col, game_map.rows - 1 - row)
        for col, row in (creature.tile_pos for creature in fauna if creature.kind == "wild_archer")
    ]
    assert len(edge_distances) == 40
    assert set(edge_distances) == {1, 2, 3}
