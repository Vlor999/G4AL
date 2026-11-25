import pytest

from game.npcs.actions import ActionType, State
from game.npcs.archer import Archer
from game.npcs.npc import NPC
from game.orders.direct_orders import DirectOrder, DirectOrderOutcome, apply_direct_order
from game.resources.storage import ResourceStorage
from game.world.map import GameMap
from tests.conftest import MapBuilder

OPEN_FIELD = ["......"] * 4
UNKNOWN_NPC_ID = -1


def make_world(build_map: MapBuilder) -> tuple[GameMap, list[NPC]]:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    npcs: list[NPC] = []
    npcs.append(NPC(*game_map.tile_center(0, 0), game_map, [], storage))
    npcs.append(Archer(*game_map.tile_center(5, 3), game_map, [], storage))
    for npc in npcs:
        # A busy NPC only queues the action, so the test reads it before it starts.
        npc.state = State.MOVING
    return game_map, npcs


@pytest.mark.parametrize(
    ("npc_index", "action_type", "target", "expected_outcome"),
    [
        (0, ActionType.MOVE_TO, (5, 3), DirectOrderOutcome.ACCEPTED),
        (0, ActionType.CHOP_WOOD, None, DirectOrderOutcome.ACCEPTED),
        (1, ActionType.CHOP_WOOD, None, DirectOrderOutcome.REFUSED_BY_NPC),
        (None, ActionType.EAT, None, DirectOrderOutcome.UNKNOWN_NPC),
        (0, ActionType.MOVE_TO, (6, 0), DirectOrderOutcome.TARGET_OUTSIDE_MAP),
        (0, ActionType.BUILD, (0, -1), DirectOrderOutcome.TARGET_OUTSIDE_MAP),
    ],
)
def test_apply_direct_order_reports_what_became_of_the_order(
    build_map: MapBuilder,
    npc_index: int | None,
    action_type: ActionType,
    target: tuple[int, int] | None,
    expected_outcome: DirectOrderOutcome,
) -> None:
    game_map, npcs = make_world(build_map)
    npc_id = UNKNOWN_NPC_ID if npc_index is None else npcs[npc_index].id
    order = DirectOrder(npc_id=npc_id, action_type=action_type, target=target)

    outcome = apply_direct_order(order, npcs=npcs, game_map=game_map)

    assert outcome is expected_outcome
    queued_counts = [len(npc.action_queue) for npc in npcs]
    expected_counts = [1, 0] if expected_outcome is DirectOrderOutcome.ACCEPTED else [0, 0]
    assert queued_counts == expected_counts


def test_apply_direct_order_aims_a_build_order_at_its_target(build_map: MapBuilder) -> None:
    game_map, npcs = make_world(build_map)
    order = DirectOrder(npc_id=npcs[0].id, action_type=ActionType.BUILD, target=(2, 3))

    apply_direct_order(order, npcs=npcs, game_map=game_map)

    [queued] = npcs[0].action_queue
    assert queued.target == (2, 3)


def test_move_to_without_target_cannot_be_built() -> None:
    with pytest.raises(ValueError, match="move_to needs a target tile"):
        DirectOrder(npc_id=1, action_type=ActionType.MOVE_TO)
