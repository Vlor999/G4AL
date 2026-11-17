import pytest

from game.entities import Rock, Structure, Tree, WheatField, spawn_resources
from game.settings import (
    ROCK_GOLD_YIELD,
    ROCK_STONE_YIELD,
    TREE_WOOD_YIELD,
    WHEAT_GROW_TIME,
    WHEAT_YIELD,
)
from tests.conftest import MapBuilder


def test_collect_one_unit_depletes_tree_after_its_yield() -> None:
    tree = Tree(0, 0)
    collected = [tree.collect_one_unit() for _ in range(TREE_WOOD_YIELD)]
    assert collected == [("wood", 1)] * TREE_WOOD_YIELD
    assert tree.depleted
    assert tree.hp == 0
    assert tree.collect_one_unit() is None


def test_collect_one_unit_takes_stone_then_gold() -> None:
    rock = Rock(0, 0, has_gold=True)
    kinds = [unit[0] for unit in iter(rock.collect_one_unit, None)]
    assert kinds == ["stone"] * ROCK_STONE_YIELD + ["gold"] * ROCK_GOLD_YIELD


def test_harvest_tick_returns_yields_once_hp_runs_out() -> None:
    tree = Tree(0, 0)
    results = [tree.harvest_tick() for _ in range(tree.max_hp)]
    assert results[:-1] == [None] * (tree.max_hp - 1)
    assert results[-1] == {"wood": TREE_WOOD_YIELD}
    assert tree.harvest_tick() is None


def test_wheat_grows_fully_after_grow_time() -> None:
    field = WheatField(0, 0)
    for _ in range(WHEAT_GROW_TIME - 1):
        field.grow_tick()
    assert not field.fully_grown
    assert field.harvest_tick() is None
    field.grow_tick()
    assert field.fully_grown
    assert field.growth_ratio == 1.0


def test_grown_wheat_harvest_yields_wheat() -> None:
    field = WheatField(0, 0)
    for _ in range(WHEAT_GROW_TIME):
        field.grow_tick()
    results = [field.harvest_tick() for _ in range(field.max_hp)]
    assert results[-1] == {"wheat": WHEAT_YIELD}
    assert field.depleted


@pytest.mark.parametrize(("ticks", "expected_built"), [(99, False), (100, True)])
def test_structure_is_built_after_one_hundred_ticks(ticks: int, expected_built: bool) -> None:
    structure = Structure(0, 0)
    for _ in range(ticks):
        structure.build_tick()
    assert structure.built is expected_built


@pytest.mark.parametrize(
    ("building_type", "expected_tile_count"),
    [("house1", 4), ("castle", 15), ("unknown", 4)],
)
def test_occupied_tiles_cover_grid_footprint(building_type: str, expected_tile_count: int) -> None:
    structure = Structure(3, 4, building_type=building_type)
    tiles = structure.occupied_tiles
    assert len(tiles) == expected_tile_count
    assert (3, 4) in tiles


def test_spawn_resources_places_only_on_free_walkable_tiles(build_map: MapBuilder) -> None:
    game_map = build_map(["~~~~~~~~"] + ["~......~"] * 6 + ["~~~~~~~~"])
    resources = spawn_resources(game_map, tree_count=5, rock_count=3)
    positions = [(resource.col, resource.row) for resource in resources]
    assert len(positions) == len(set(positions)) == 8
    assert all(game_map.is_walkable(col, row) for col, row in positions)
