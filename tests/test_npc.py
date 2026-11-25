"""Pawn action planning on hand-built worlds: harvest and hut trips, build, farm, move, eat."""

from collections.abc import Callable

import pytest

from game.actions import Action, ActionType, State
from game.archer import Archer
from game.entities import Resource, Rock, Structure, Tree, WheatField
from game.map import GameMap
from game.npc import NPC
from game.settings import (
    BUILD_COST_STONE,
    BUILD_COST_WOOD,
    EAT_WHEAT_COST,
    HOUSE_CAPACITY_BONUS,
    NPC_EAT_RESTORE,
    NPC_EAT_TIME,
    NPC_MAX_HEALTH,
    STORAGE_BASE_CAPACITY,
    WHEAT_GROW_TIME,
)
from game.storage import ResourceStorage
from tests.conftest import MapBuilder

OPEN_FIELD = ["......"] * 4
WIDE_FIELD = ["........"] * 5
# One grass tile in a lake: no free tile around it, no 2x2 area to build on.
ISLAND_TILE = ["~~~", "~.~", "~~~"]
# The hut sits on grass walled in by water: no tile next to it is walkable.
WALLED_HUT_FIELD = ["........", "...~~~~.", "...~..~.", "...~..~.", "...~~~~."]
# Water splits the map: the hut is on the far side of the pawn and its tree.
SPLIT_FIELD = ["..~.....", "..~.....", "..~.....", "..~....."]

MAX_FRAMES = 5000


def make_pawn(
    game_map: GameMap,
    tile: tuple[int, int],
    *,
    resources: list[Resource] | None = None,
    storage: ResourceStorage | None = None,
    hut: Structure | None = None,
) -> NPC:
    x, y = game_map.tile_center(*tile)
    return NPC(
        x,
        y,
        game_map,
        resources if resources is not None else [],
        storage if storage is not None else ResourceStorage(),
        name="Bob",
        hut=hut,
    )


def run_until(npc: NPC, is_reached: Callable[[], bool], max_frames: int = MAX_FRAMES) -> bool:
    """Update ``npc`` frame by frame until ``is_reached``; False when ``max_frames`` ran out."""
    for _ in range(max_frames):
        if is_reached():
            return True
        npc.update()
    return is_reached()


def ripe_wheat(col: int, row: int) -> WheatField:
    field = WheatField(col, row)
    for _ in range(WHEAT_GROW_TIME):
        field.grow_tick()
    return field


@pytest.mark.parametrize(
    ("npc_class", "action_type", "expected"),
    [
        (NPC, ActionType.SHOOT, False),
        (NPC, ActionType.EAT, True),
        (Archer, ActionType.CHOP_WOOD, False),
        (Archer, ActionType.DEFEND, True),
    ],
)
def test_enqueue_accepts_only_allowed_actions(
    build_map: MapBuilder, npc_class: type[NPC], action_type: ActionType, expected: bool
) -> None:
    game_map = build_map(OPEN_FIELD)
    npc = npc_class(0.0, 0.0, game_map, [], ResourceStorage(), name="Robin")
    assert npc.enqueue(Action(action_type)) is expected


@pytest.mark.parametrize("npc_class", [NPC, Archer])
def test_eat_spends_wheat_and_restores_hunger(build_map: MapBuilder, npc_class: type[NPC]) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    storage.add("wheat", EAT_WHEAT_COST)
    npc = npc_class(*game_map.tile_center(0, 0), game_map, [], storage, name="Bob")
    npc.hunger = 10.0
    npc.enqueue(Action(ActionType.EAT))
    for _ in range(NPC_EAT_TIME):
        npc.update()
    assert storage.wheat == 0
    assert npc.hunger > 10.0 + NPC_EAT_RESTORE - 1
    assert npc.state == State.DONE


@pytest.mark.parametrize("npc_class", [NPC, Archer])
def test_eat_without_wheat_is_refused(build_map: MapBuilder, npc_class: type[NPC]) -> None:
    game_map = build_map(OPEN_FIELD)
    npc = npc_class(*game_map.tile_center(0, 0), game_map, [], ResourceStorage(), name="Bob")
    npc.enqueue(Action(ActionType.EAT))
    assert npc.state == State.DONE


@pytest.mark.parametrize(("hunger", "is_hurt"), [(0.0, True), (50.0, False)])
def test_an_npc_loses_health_only_when_starving(
    build_map: MapBuilder, hunger: float, is_hurt: bool
) -> None:
    npc = make_pawn(build_map(OPEN_FIELD), (0, 0))
    npc.hunger = hunger

    npc.update()

    assert (npc.health < NPC_MAX_HEALTH) is is_hurt


def test_move_to_walks_to_the_tile_then_idles(build_map: MapBuilder) -> None:
    npc = make_pawn(build_map(OPEN_FIELD), (0, 0))

    npc.enqueue(Action(ActionType.MOVE_TO, target=(4, 2)))

    assert npc.state == State.MOVING
    assert run_until(npc, lambda: npc.state == State.IDLE)
    assert npc.tile_pos == (4, 2)


def test_queued_moves_run_one_after_the_other(build_map: MapBuilder) -> None:
    npc = make_pawn(build_map(OPEN_FIELD), (0, 0))

    npc.enqueue(Action(ActionType.MOVE_TO, target=(3, 0)))
    npc.enqueue(Action(ActionType.MOVE_TO, target=(3, 3)))

    assert npc.queue_size == 2
    assert run_until(npc, lambda: npc.state == State.IDLE)
    assert npc.tile_pos == (3, 3)


def test_chop_wood_carries_each_unit_to_the_hut_and_goes_back_to_the_tree(
    build_map: MapBuilder,
) -> None:
    game_map = build_map(WIDE_FIELD)
    storage = ResourceStorage()
    hut = Structure(5, 0, building_type="storage_hut")
    tree = Tree(2, 3)
    npc = make_pawn(game_map, (0, 3), resources=[hut, tree], storage=storage, hut=hut)

    npc.enqueue(Action(ActionType.CHOP_WOOD))

    assert run_until(npc, lambda: npc.state == State.RETURNING)
    assert npc.carrying == {"wood": 1}
    assert run_until(npc, lambda: storage.wood == 2)
    assert tree.reserved_by == npc.id
    assert tree.remaining_yields == {"wood": 8}


@pytest.mark.parametrize(
    ("rows", "hut"),
    [
        (WIDE_FIELD, None),
        (WALLED_HUT_FIELD, Structure(4, 2, building_type="storage_hut")),
        (SPLIT_FIELD, Structure(4, 1, building_type="storage_hut")),
    ],
    ids=["no-hut", "hut-walled-in", "hut-unreachable"],
)
def test_a_pawn_that_cannot_reach_a_hut_deposits_where_it_stands(
    build_map: MapBuilder, rows: list[str], hut: Structure | None
) -> None:
    game_map = build_map(rows)
    storage = ResourceStorage()
    tree = Tree(1, 1)
    npc = make_pawn(game_map, (0, 0), resources=[tree], storage=storage, hut=hut)

    npc.enqueue(Action(ActionType.CHOP_WOOD))

    assert run_until(npc, lambda: storage.wood == 1)
    assert npc.state != State.RETURNING
    assert npc.carrying == {}


def test_a_queued_order_runs_after_the_deposit_instead_of_the_harvest_loop(
    build_map: MapBuilder,
) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    tree = Tree(1, 0)
    npc = make_pawn(game_map, (0, 0), resources=[tree], storage=storage)
    npc.enqueue(Action(ActionType.CHOP_WOOD))
    assert run_until(npc, lambda: npc.state == State.PERFORMING)

    npc.enqueue(Action(ActionType.MOVE_TO, target=(4, 3)))

    assert run_until(npc, lambda: npc.state == State.IDLE)
    assert npc.tile_pos == (4, 3)
    assert storage.wood == 1
    assert tree.reserved_by is None


def test_a_pawn_goes_idle_once_its_tree_is_used_up(build_map: MapBuilder) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    tree = Tree(1, 0)
    tree.remaining_yields = {"wood": 1}
    npc = make_pawn(game_map, (0, 0), resources=[tree], storage=storage)

    npc.enqueue(Action(ActionType.CHOP_WOOD))

    assert run_until(npc, lambda: npc.state == State.IDLE)
    assert tree.depleted
    assert storage.wood == 1


def test_a_pawn_keeps_its_load_while_storage_is_full_then_stores_it(
    build_map: MapBuilder,
) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    storage.add("stone", STORAGE_BASE_CAPACITY)
    tree = Tree(1, 0)
    tree.remaining_yields = {"wood": 1}
    npc = make_pawn(game_map, (0, 0), resources=[tree], storage=storage)
    npc.enqueue(Action(ActionType.CHOP_WOOD))
    assert run_until(npc, lambda: npc.state == State.WAITING_DEPOSIT)

    npc.update()
    assert npc.state == State.WAITING_DEPOSIT
    assert npc.carrying == {"wood": 1}
    assert tree.depleted

    storage.discard("stone", STORAGE_BASE_CAPACITY)

    assert run_until(npc, lambda: npc.state == State.IDLE)
    assert storage.wood == 1
    assert npc.carrying == {}
    assert not npc.is_carrying


@pytest.mark.parametrize(
    ("stone_stored", "load", "queued_order", "stored_wood", "kept_load"),
    [
        (STORAGE_BASE_CAPACITY, {"wood": 1}, None, 0, {"wood": 1}),
        (STORAGE_BASE_CAPACITY - 1, {"wood": 2}, None, 1, {"wood": 1}),
        (STORAGE_BASE_CAPACITY - 1, {"wood": 1}, None, 1, {}),
        (
            STORAGE_BASE_CAPACITY,
            {"wood": 1},
            Action(ActionType.MOVE_TO, target=(3, 2)),
            0,
            {"wood": 1},
        ),
    ],
    ids=["no-room", "partial-room", "exactly-full", "no-room-with-queued-order"],
)
def test_a_pawn_at_a_full_storage_keeps_what_does_not_fit_and_waits(
    build_map: MapBuilder,
    stone_stored: int,
    load: dict[str, int],
    queued_order: Action | None,
    stored_wood: int,
    kept_load: dict[str, int],
) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    storage.add("stone", stone_stored)
    npc = make_pawn(game_map, (0, 0), storage=storage)
    npc.carrying = dict(load)
    npc.is_carrying = True
    npc.state = State.RETURNING
    if queued_order is not None:
        npc.enqueue(queued_order)

    npc.update()

    assert npc.state == State.WAITING_DEPOSIT
    assert npc.carrying == kept_load
    assert storage.wood == stored_wood
    assert storage.total == STORAGE_BASE_CAPACITY
    assert len(npc.action_queue) == (0 if queued_order is None else 1)

    storage.discard("stone", STORAGE_BASE_CAPACITY)

    assert run_until(npc, lambda: npc.state == State.IDLE and not npc.action_queue)
    assert npc.carrying == {}
    assert not npc.is_carrying
    assert storage.wood == sum(load.values())
    if queued_order is not None:
        assert npc.tile_pos == queued_order.target


def empty_world(build_map: MapBuilder) -> tuple[GameMap, list[Resource], ResourceStorage]:
    return build_map(OPEN_FIELD), [], ResourceStorage()


def world_with_unripe_wheat(
    build_map: MapBuilder,
) -> tuple[GameMap, list[Resource], ResourceStorage]:
    return build_map(OPEN_FIELD), [WheatField(2, 2)], ResourceStorage()


def world_with_a_reserved_tree(
    build_map: MapBuilder,
) -> tuple[GameMap, list[Resource], ResourceStorage]:
    tree = Tree(2, 2)
    tree.reserved_by = 999
    return build_map(OPEN_FIELD), [tree], ResourceStorage()


def island_with_building_stock(
    build_map: MapBuilder,
) -> tuple[GameMap, list[Resource], ResourceStorage]:
    storage = ResourceStorage()
    storage.add("wood", BUILD_COST_WOOD)
    storage.add("stone", BUILD_COST_STONE)
    return build_map(ISLAND_TILE), [], storage


def island_under_a_rock(
    build_map: MapBuilder,
) -> tuple[GameMap, list[Resource], ResourceStorage]:
    return build_map(ISLAND_TILE), [Rock(1, 1)], ResourceStorage()


WorldBuilder = Callable[[MapBuilder], tuple[GameMap, list[Resource], ResourceStorage]]


@pytest.mark.parametrize(
    ("build_world", "pawn_tile", "action"),
    [
        (empty_world, (0, 0), Action(ActionType.CHOP_WOOD)),
        (empty_world, (0, 0), Action(ActionType.MINE_ROCK)),
        (world_with_a_reserved_tree, (0, 0), Action(ActionType.CHOP_WOOD)),
        (world_with_unripe_wheat, (0, 0), Action(ActionType.COLLECT_WHEAT)),
        (empty_world, (0, 0), Action(ActionType.BUILD, target=(2, 1))),
        (island_with_building_stock, (1, 1), Action(ActionType.BUILD, target=(1, 1))),
        (island_under_a_rock, (1, 1), Action(ActionType.PLANT_WHEAT, target=(1, 1))),
        (empty_world, (0, 0), Action(ActionType.MOVE_TO)),
        (island_with_building_stock, (1, 1), Action(ActionType.MOVE_TO, target=(5, 5))),
    ],
    ids=[
        "chop-without-tree",
        "mine-without-rock",
        "chop-reserved-tree",
        "collect-unripe-wheat",
        "build-without-resources",
        "build-without-space",
        "plant-without-space",
        "move-without-target",
        "move-out-of-reach",
    ],
)
def test_an_order_the_world_cannot_satisfy_ends_at_once(
    build_map: MapBuilder,
    build_world: WorldBuilder,
    pawn_tile: tuple[int, int],
    action: Action,
) -> None:
    game_map, resources, storage = build_world(build_map)
    resources_before = list(resources)
    stock_before = storage.snapshot()
    npc = make_pawn(game_map, pawn_tile, resources=resources, storage=storage)

    npc.enqueue(action)
    state_after_order = npc.state

    assert state_after_order == State.DONE
    assert resources == resources_before
    assert storage.snapshot() == stock_before
    npc.update()
    assert npc.state == State.IDLE


def test_build_spends_the_cost_and_completes_a_house_that_raises_capacity(
    build_map: MapBuilder,
) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    storage.add("wood", BUILD_COST_WOOD)
    storage.add("stone", BUILD_COST_STONE)
    resources: list[Resource] = []
    npc = make_pawn(game_map, (0, 0), resources=resources, storage=storage)

    npc.enqueue(Action(ActionType.BUILD, target=(3, 1)))

    [house] = resources
    assert isinstance(house, Structure)
    assert (house.col, house.row) == (3, 1)
    assert (storage.wood, storage.stone) == (0, 0)
    assert run_until(npc, lambda: npc.state == State.IDLE)
    assert house.built
    assert storage.capacity == STORAGE_BASE_CAPACITY + HOUSE_CAPACITY_BONUS


def test_build_on_a_started_structure_finishes_it_without_spending(
    build_map: MapBuilder,
) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    structure = Structure(3, 1, build_progress=50, building_type="tower")
    npc = make_pawn(game_map, (0, 0), resources=[structure], storage=storage)

    npc.enqueue(Action(ActionType.BUILD, target=structure))

    assert run_until(npc, lambda: npc.state == State.IDLE)
    assert structure.built
    assert storage.capacity == STORAGE_BASE_CAPACITY


@pytest.mark.parametrize(
    ("obstacles", "expected_tile"),
    [([], (3, 1)), ([Tree(3, 1)], (2, 1))],
    ids=["free-tile", "tile-taken-by-a-tree"],
)
def test_plant_wheat_sows_a_field_on_the_nearest_free_tile(
    build_map: MapBuilder, obstacles: list[Resource], expected_tile: tuple[int, int]
) -> None:
    game_map = build_map(OPEN_FIELD)
    resources = list(obstacles)
    npc = make_pawn(game_map, (0, 0), resources=resources)

    npc.enqueue(Action(ActionType.PLANT_WHEAT, target=(3, 1)))

    [field] = [resource for resource in resources if isinstance(resource, WheatField)]
    assert (field.col, field.row) == expected_tile
    assert run_until(npc, lambda: npc.state == State.IDLE)
    assert npc.tile_pos == expected_tile


def test_collect_wheat_harvests_the_nearest_ripe_field(build_map: MapBuilder) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    unripe = WheatField(1, 0)
    ripe = ripe_wheat(4, 0)
    npc = make_pawn(game_map, (0, 0), resources=[unripe, ripe], storage=storage)

    npc.enqueue(Action(ActionType.COLLECT_WHEAT))

    assert run_until(npc, lambda: storage.wheat == 1)
    assert unripe.remaining_yields == unripe.yields


@pytest.mark.parametrize(
    ("state", "expected_released"), [(State.WAITING_DEPOSIT, True), (State.MOVING, False)]
)
def test_give_up_waiting_deposit_drops_the_load_only_when_waiting(
    build_map: MapBuilder, state: State, expected_released: bool
) -> None:
    npc = make_pawn(build_map(OPEN_FIELD), (0, 0))
    npc.state = state
    npc.is_carrying = True
    npc.carrying = {"wood": 3}

    assert npc.give_up_waiting_deposit() is expected_released

    assert npc.state == (State.IDLE if expected_released else state)
    assert npc.carrying == ({} if expected_released else {"wood": 3})
    assert npc.is_carrying is not expected_released


@pytest.mark.parametrize("npc_class", [NPC, Archer])
def test_hunger_drains_before_the_meal_that_ends_in_the_same_frame(
    build_map: MapBuilder, npc_class: type[NPC]
) -> None:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    storage.add("wheat", EAT_WHEAT_COST)
    npc = npc_class(*game_map.tile_center(0, 0), game_map, [], storage, name="Bob")
    npc.enqueue(Action(ActionType.EAT))

    for _ in range(NPC_EAT_TIME):
        npc.update()

    assert npc.state == State.DONE
    assert npc.hunger == npc.max_hunger


def test_pawn_has_a_starter_for_each_pawn_action() -> None:
    assert set(NPC._START_BY_ACTION) == set(NPC.allowed_actions)


@pytest.mark.parametrize("action_type", Archer.allowed_actions)
def test_the_archer_reacts_to_each_archer_action(
    build_map: MapBuilder, action_type: ActionType
) -> None:
    game_map = build_map(OPEN_FIELD)
    archer = Archer(*game_map.tile_center(0, 0), game_map, [], ResourceStorage(), name="Robin")
    archer.enqueue(Action(action_type, target=(3, 2)))

    archer.update()

    assert archer.state != State.IDLE or archer.visible_speech_text
