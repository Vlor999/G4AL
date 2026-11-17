import pytest

from game.actions import Action, ActionType, State
from game.archer import Archer
from game.entities import Resource, Tree
from game.npc import NPC
from game.settings import EAT_WHEAT_COST, NPC_EAT_RESTORE, NPC_EAT_TIME
from game.storage import ResourceStorage
from tests.conftest import MapBuilder

OPEN_FIELD = ["......"] * 4


def make_npc(build_map: MapBuilder, resources: list[Resource], storage: ResourceStorage) -> NPC:
    game_map = build_map(OPEN_FIELD)
    x, y = game_map.tile_center(0, 0)
    return NPC(x, y, game_map, resources, storage, name="Bob")


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


def test_eat_spends_wheat_and_restores_hunger(build_map: MapBuilder) -> None:
    storage = ResourceStorage()
    storage.add("wheat", EAT_WHEAT_COST)
    npc = make_npc(build_map, [], storage)
    npc.hunger = 10.0
    npc.enqueue(Action(ActionType.EAT))
    for _ in range(NPC_EAT_TIME):
        npc.update()
    assert storage.wheat == 0
    assert npc.hunger > 10.0 + NPC_EAT_RESTORE - 1
    assert npc.state == State.DONE


def test_eat_without_wheat_is_refused(build_map: MapBuilder) -> None:
    npc = make_npc(build_map, [], ResourceStorage())
    npc.enqueue(Action(ActionType.EAT))
    assert npc.state == State.DONE


def test_chop_wood_brings_wood_to_storage(build_map: MapBuilder) -> None:
    storage = ResourceStorage()
    tree = Tree(3, 0)
    npc = make_npc(build_map, [tree], storage)
    npc.enqueue(Action(ActionType.CHOP_WOOD))
    assert tree.reserved_by == npc.id
    for _ in range(400):
        npc.update()
    assert storage.wood >= 1


@pytest.mark.parametrize(
    ("state", "expected_released"), [(State.WAITING_DEPOSIT, True), (State.MOVING, False)]
)
def test_give_up_waiting_deposit_drops_the_load_only_when_waiting(
    build_map: MapBuilder, state: State, expected_released: bool
) -> None:
    npc = make_npc(build_map, [], ResourceStorage())
    npc.state = state
    npc.is_carrying = True
    npc.carrying = {"wood": 3}

    assert npc.give_up_waiting_deposit() is expected_released

    assert npc.state == (State.IDLE if expected_released else state)
    assert npc.carrying == ({} if expected_released else {"wood": 3})
    assert npc.is_carrying is not expected_released
