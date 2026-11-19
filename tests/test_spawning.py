from game.archer import Archer
from game.map import GameMap
from game.npc import NPC
from game.settings import (
    ARCHER_SPAWN_MAX_DISTANCE,
    INITIAL_ARCHER_COUNT,
    INITIAL_PAWN_COUNT,
    INITIAL_SHEEP_COUNT,
    INITIAL_WILD_ARCHER_COUNT,
    MAP_COLS,
    MAP_ROWS,
    PAWN_SPAWN_RADIUS,
    STORAGE_HUT_COL,
    STORAGE_HUT_ROW,
)
from game.sheep import Sheep
from game.spawning import spawn_world
from game.wild_archer import WildArcher
from tests.conftest import MapBuilder


def build_meadow(build_map: MapBuilder) -> GameMap:
    return build_map(["." * MAP_COLS] * MAP_ROWS)


def test_spawn_world_places_a_built_storage_hut_among_resources(build_map: MapBuilder) -> None:
    world = spawn_world(build_meadow(build_map))

    assert world.storage_hut.built
    assert (world.storage_hut.col, world.storage_hut.row) == (STORAGE_HUT_COL, STORAGE_HUT_ROW)
    assert world.storage_hut in world.resources
    assert world.storage.total == 0


def test_spawn_world_places_pawns_near_the_center_and_archers_near_the_hut(
    build_map: MapBuilder,
) -> None:
    game_map = build_meadow(build_map)

    world = spawn_world(game_map)

    pawns = [npc for npc in world.npcs if type(npc) is NPC]
    archers = [npc for npc in world.npcs if isinstance(npc, Archer)]
    assert len(pawns) == INITIAL_PAWN_COUNT
    assert len(archers) == INITIAL_ARCHER_COUNT
    for pawn in pawns:
        col, row = pawn.tile_pos
        assert abs(col - game_map.cols // 2) <= PAWN_SPAWN_RADIUS
        assert abs(row - game_map.rows // 2) <= PAWN_SPAWN_RADIUS
    for archer in archers:
        col, row = archer.tile_pos
        assert max(abs(col - STORAGE_HUT_COL), abs(row - STORAGE_HUT_ROW)) <= (
            ARCHER_SPAWN_MAX_DISTANCE
        )


def test_spawn_world_puts_no_npc_on_a_resource_or_another_npc(build_map: MapBuilder) -> None:
    world = spawn_world(build_meadow(build_map))

    npc_tiles = [npc.tile_pos for npc in world.npcs]
    resource_tiles = {(resource.col, resource.row) for resource in world.resources}
    resource_tiles.update(world.storage_hut.occupied_tiles)
    assert len(set(npc_tiles)) == len(npc_tiles)
    assert not resource_tiles & set(npc_tiles)


def test_spawn_world_adds_sheep_and_a_wild_archer_camp_in_the_bottom_right(
    build_map: MapBuilder,
) -> None:
    game_map = build_meadow(build_map)

    world = spawn_world(game_map)

    wild_archers = [creature for creature in world.fauna if isinstance(creature, WildArcher)]
    assert sum(isinstance(creature, Sheep) for creature in world.fauna) == INITIAL_SHEEP_COUNT
    assert len(wild_archers) == INITIAL_WILD_ARCHER_COUNT
    for wild_archer in wild_archers:
        col, row = wild_archer.tile_pos
        assert col >= game_map.cols // 2
        assert row >= game_map.rows // 2


def test_spawn_world_shares_the_combat_lists_between_archers_and_wild_archers(
    build_map: MapBuilder,
) -> None:
    world = spawn_world(build_meadow(build_map))

    for npc in world.npcs:
        if isinstance(npc, Archer):
            assert npc._all_fauna is world.fauna
            assert npc._arrows is world.arrows
    for creature in world.fauna:
        if isinstance(creature, WildArcher):
            assert creature._all_npcs is world.npcs
            assert creature._arrows is world.arrows
