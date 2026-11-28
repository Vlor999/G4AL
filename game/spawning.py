"""Initial population of a new game: resources, storage hut, NPCs and fauna."""

from __future__ import annotations

from dataclasses import dataclass, field

from game.combat.arrows import Arrow
from game.constants import BUILD_PROGRESS_COMPLETE
from game.fauna.fauna import Fauna
from game.fauna.fauna_spawning import spawn_fauna
from game.fauna.wild_archer import WildArcher
from game.npcs.archer import Archer
from game.npcs.npc import NPC
from game.resources.entities import Resource, Structure, spawn_resources
from game.resources.storage import ResourceStorage
from game.settings import (
    ARCHER_SPAWN_MAX_DISTANCE,
    INITIAL_ARCHER_COUNT,
    INITIAL_PAWN_COUNT,
    INITIAL_SHEEP_COUNT,
    INITIAL_WILD_ARCHER_COUNT,
    PAWN_SPAWN_RADIUS,
    WILD_ARCHER_CORNER_MARGIN,
    WILD_ARCHER_SPAWN_RADIUS,
)
from game.world.clock import WorldClock
from game.world.dimensions import OBJECT_DIMENSIONS, ObjectKind
from game.world.map import GameMap


@dataclass
class SpawnedWorld:
    """The settlement at frame zero.

    ``resources`` includes ``storage_hut``. The lists and the clock are shared by
    reference with the NPCs and creatures that read them: mutate them in place to keep
    those links.
    """

    storage: ResourceStorage
    resources: list[Resource]
    storage_hut: Structure
    npcs: list[NPC] = field(default_factory=list)
    fauna: list[Fauna] = field(default_factory=list)
    arrows: list[Arrow] = field(default_factory=list)
    clock: WorldClock = field(default_factory=WorldClock)


def spawn_world(game_map: GameMap) -> SpawnedWorld:
    """Populate ``game_map``, drawing from ``game_map.rng``: the built storage hut,
    resources by biome around it, pawns around the map centre, archers around the hut,
    sheep, a cat and a wild archer camp in the bottom-right corner."""
    hut_col, hut_row = _storage_hut_origin(game_map)
    storage_hut = Structure(
        hut_col, hut_row, build_progress=BUILD_PROGRESS_COMPLETE, building_type="storage_hut"
    )
    storage_hut.built = True
    resources = spawn_resources(game_map, reserved=set(storage_hut.occupied_tiles))
    resources.append(storage_hut)
    world = SpawnedWorld(ResourceStorage(), resources, storage_hut)

    entity_tiles = _occupied_entity_tiles(resources)
    _spawn_pawns_near_center(world, game_map, entity_tiles=entity_tiles)
    _spawn_archers_near_hut(world, game_map, entity_tiles=entity_tiles)
    world.fauna = spawn_fauna(game_map, resources, sheep_count=INITIAL_SHEEP_COUNT)
    _spawn_wild_archers_in_corner(world, game_map)
    _link_combatants(world)
    return world


def _storage_hut_origin(game_map: GameMap) -> tuple[int, int]:
    """Top-left tile of the hut: its footprint is centred on the map's centre column and
    starts on the centre row."""
    half_width = OBJECT_DIMENSIONS[ObjectKind.STORAGE_HUT].footprint_width // 2
    return game_map.cols // 2 - half_width, game_map.rows // 2


def _occupied_entity_tiles(resources: list[Resource]) -> set[tuple[int, int]]:
    return {tile for resource in resources for tile in resource.occupied_tiles}


def _spawn_pawns_near_center(
    world: SpawnedWorld, game_map: GameMap, *, entity_tiles: set[tuple[int, int]]
) -> None:
    center_col, center_row = game_map.cols // 2, game_map.rows // 2
    placed = 0
    for dc in range(-PAWN_SPAWN_RADIUS, PAWN_SPAWN_RADIUS + 1):
        for dr in range(-PAWN_SPAWN_RADIUS, PAWN_SPAWN_RADIUS + 1):
            col, row = center_col + dc, center_row + dr
            if not game_map.is_walkable(col, row) or (col, row) in entity_tiles:
                continue
            x, y = game_map.tile_center(col, row)
            world.npcs.append(
                NPC(
                    x,
                    y,
                    game_map,
                    world.resources,
                    world.storage,
                    hut=world.storage_hut,
                )
            )
            entity_tiles.add((col, row))
            placed += 1
            if placed >= INITIAL_PAWN_COUNT:
                return


def _spawn_archers_near_hut(
    world: SpawnedWorld, game_map: GameMap, *, entity_tiles: set[tuple[int, int]]
) -> None:
    placed = 0
    for col, row in _rings_around(world.storage_hut.col, world.storage_hut.row):
        if not game_map.is_walkable(col, row) or (col, row) in entity_tiles:
            continue
        x, y = game_map.tile_center(col, row)
        world.npcs.append(Archer(x, y, game_map, world.resources, world.storage))
        entity_tiles.add((col, row))
        placed += 1
        if placed >= INITIAL_ARCHER_COUNT:
            return


def _rings_around(center_col: int, center_row: int) -> list[tuple[int, int]]:
    """Tiles on square rings at distance 1 to ``ARCHER_SPAWN_MAX_DISTANCE``, nearest first."""
    tiles: list[tuple[int, int]] = []
    for distance in range(1, ARCHER_SPAWN_MAX_DISTANCE + 1):
        for dc in range(-distance, distance + 1):
            for dr in range(-distance, distance + 1):
                if abs(dc) == distance or abs(dr) == distance:
                    tiles.append((center_col + dc, center_row + dr))
    return tiles


def _spawn_wild_archers_in_corner(world: SpawnedWorld, game_map: GameMap) -> None:
    camp_col = game_map.cols - WILD_ARCHER_CORNER_MARGIN
    camp_row = game_map.rows - WILD_ARCHER_CORNER_MARGIN
    # Only resource origins are avoided here, not every tile of a structure.
    occupied = {(resource.col, resource.row) for resource in world.resources}
    placed = 0
    for dc in range(-WILD_ARCHER_SPAWN_RADIUS, WILD_ARCHER_SPAWN_RADIUS + 1):
        for dr in range(-WILD_ARCHER_SPAWN_RADIUS, WILD_ARCHER_SPAWN_RADIUS + 1):
            col, row = camp_col + dc, camp_row + dr
            if not game_map.is_walkable(col, row) or (col, row) in occupied:
                continue
            x, y = game_map.tile_center(col, row)
            world.fauna.append(WildArcher(x, y, game_map))
            occupied.add((col, row))
            placed += 1
            if placed >= INITIAL_WILD_ARCHER_COUNT:
                return


def _link_combatants(world: SpawnedWorld) -> None:
    for npc in world.npcs:
        if isinstance(npc, Archer):
            npc.link_battlefield(fauna=world.fauna, arrows=world.arrows)
    for creature in world.fauna:
        if isinstance(creature, WildArcher):
            creature.link_battlefield(npcs=world.npcs, arrows=world.arrows, clock=world.clock)
