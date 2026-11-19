"""Biome terrain of generated maps: replay from a seed, regions, reachability."""

import random
from collections import deque

import pytest

from game.archer import Archer
from game.entities import Rock, Structure, spawn_resources
from game.map import GameMap
from game.settings import (
    HOME_MEADOW_RADIUS,
    INITIAL_ARCHER_COUNT,
    INITIAL_PAWN_COUNT,
    INITIAL_WILD_ARCHER_COUNT,
    MAP_COLS,
    MAP_ROWS,
    STORAGE_HUT_COL,
    STORAGE_HUT_ROW,
)
from game.spawning import SpawnedWorld, spawn_world
from game.terrain import Biome, TileType
from game.wild_archer import WildArcher

SEEDS = range(8)


def snapshot(world: SpawnedWorld) -> list[tuple[str, int, int]]:
    things = [(resource.kind, resource.col, resource.row) for resource in world.resources]
    things += [(npc.kind, *npc.tile_pos) for npc in world.npcs]
    things += [(creature.kind, *creature.tile_pos) for creature in world.fauna]
    return things


def reachable_from(game_map: GameMap, start: tuple[int, int]) -> set[tuple[int, int]]:
    reached = {start}
    queue = deque([start])
    while queue:
        col, row = queue.popleft()
        for neighbour in ((col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)):
            if neighbour not in reached and game_map.is_walkable(*neighbour):
                reached.add(neighbour)
                queue.append(neighbour)
    return reached


def test_the_same_seed_gives_the_same_map_biomes_resources_and_creatures() -> None:
    first, second = GameMap(rng=random.Random(3)), GameMap(rng=random.Random(3))

    assert (first.tiles, first.biomes) == (second.tiles, second.biomes)
    assert snapshot(spawn_world(first)) == snapshot(spawn_world(second))


def test_map_and_resource_generation_leave_the_global_random_untouched() -> None:
    random.seed(1)
    expected = random.random()
    random.seed(1)

    spawn_resources(GameMap(seed=5))

    assert random.random() == expected


@pytest.mark.parametrize("seed", SEEDS)
def test_every_walkable_tile_is_reachable_from_the_storage_hut(seed: int) -> None:
    game_map = GameMap(seed=seed)

    walkable = {
        (col, row)
        for row in range(game_map.rows)
        for col in range(game_map.cols)
        if game_map.is_walkable(col, row)
    }
    assert reachable_from(game_map, (STORAGE_HUT_COL, STORAGE_HUT_ROW)) == walkable


@pytest.mark.parametrize("seed", SEEDS)
def test_a_generated_map_has_every_biome_and_a_dry_meadow_at_home(seed: int) -> None:
    game_map = GameMap(seed=seed)
    center_col, center_row = MAP_COLS // 2, MAP_ROWS // 2

    assert {biome for row in game_map.biomes for biome in row} == set(Biome)
    assert (game_map.cols, game_map.rows) == (MAP_COLS, MAP_ROWS)
    for row in range(MAP_ROWS):
        for col in range(MAP_COLS):
            if (col - center_col) ** 2 + (row - center_row) ** 2 <= HOME_MEADOW_RADIUS**2:
                assert game_map.biomes[row][col] == Biome.MEADOW
                assert game_map.tiles[row][col] != TileType.WATER


@pytest.mark.parametrize("seed", SEEDS)
def test_spawning_on_a_generated_map_keeps_its_guarantees(seed: int) -> None:
    world = spawn_world(GameMap(seed=seed))

    archers = [npc for npc in world.npcs if isinstance(npc, Archer)]
    wild_archers = [creature for creature in world.fauna if isinstance(creature, WildArcher)]
    assert len(world.npcs) - len(archers) == INITIAL_PAWN_COUNT
    assert len(archers) == INITIAL_ARCHER_COUNT
    assert len(wild_archers) == INITIAL_WILD_ARCHER_COUNT
    hut_tiles = set(world.storage_hut.occupied_tiles)
    assert not any(
        (resource.col, resource.row) in hut_tiles
        for resource in world.resources
        if not isinstance(resource, Structure)
    )


@pytest.mark.parametrize(
    ("kind", "biome", "minimum_share"),
    [
        ("tree", Biome.FOREST, 0.75),
        ("rock", Biome.HIGHLAND, 0.7),
        ("gold", Biome.HIGHLAND, 1.0),
        ("sheep", Biome.MEADOW, 1.0),
    ],
)
def test_resources_and_sheep_spawn_mostly_in_their_biome(
    kind: str, biome: Biome, minimum_share: float
) -> None:
    in_biome = total = 0
    for seed in SEEDS:
        game_map = GameMap(seed=seed)
        world = spawn_world(game_map)
        tiles = [
            (resource.col, resource.row) for resource in world.resources if resource.kind == kind
        ]
        tiles += [
            (resource.col, resource.row)
            for resource in world.resources
            if kind == "gold" and isinstance(resource, Rock) and resource.has_gold
        ]
        tiles += [creature.tile_pos for creature in world.fauna if creature.kind == kind]
        total += len(tiles)
        in_biome += sum(game_map.biomes[row][col] == biome for col, row in tiles)

    assert total > 0
    assert in_biome / total >= minimum_share
