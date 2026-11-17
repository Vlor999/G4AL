import pytest

from game.actions import ActionType, State
from game.npc import NPC, Archer
from game.orders import NpcOrder, apply_orders
from game.settings import TTS_MAX_SPEAKERS
from game.storage import ResourceStorage
from tests.conftest import MapBuilder

OPEN_FIELD = ["......"] * 4


def make_npcs(build_map: MapBuilder) -> list[NPC]:
    game_map = build_map(OPEN_FIELD)
    storage = ResourceStorage()
    pawn_x, pawn_y = game_map.tile_center(0, 0)
    archer_x, archer_y = game_map.tile_center(5, 3)
    npcs: list[NPC] = []
    npcs.append(NPC(pawn_x, pawn_y, game_map, [], storage, all_npcs=npcs, name="Bob"))
    npcs.append(Archer(archer_x, archer_y, game_map, [], storage, all_npcs=npcs, name="Robin"))
    return npcs


def make_order(npc: NPC, action_type: ActionType | None) -> NpcOrder:
    return NpcOrder(npc_id=npc.id, npc_name=npc.name, action_type=action_type, voice_line="On it!")


@pytest.mark.parametrize(
    ("archer_action", "expected_accepted"),
    [(ActionType.DEFEND, True), (ActionType.CHOP_WOOD, False), (None, False)],
)
def test_apply_orders_reports_whether_the_npc_took_the_action(
    build_map: MapBuilder, archer_action: ActionType | None, expected_accepted: bool
) -> None:
    archer = make_npcs(build_map)[1]

    [outcome] = apply_orders([archer], [make_order(archer, archer_action)])

    assert outcome.is_accepted is expected_accepted
    assert (archer._speech_text == "On it!") is expected_accepted


@pytest.mark.parametrize("action_type", [ActionType.BUILD, ActionType.PLANT_WHEAT])
def test_apply_orders_targets_the_npc_tile_for_build_and_plant(
    build_map: MapBuilder, action_type: ActionType
) -> None:
    pawn = make_npcs(build_map)[0]
    # A busy NPC only queues the action, so the test reads it before it starts.
    pawn.state = State.MOVING

    apply_orders([pawn], [make_order(pawn, action_type)])

    [queued] = pawn.action_queue
    assert queued.action_type is action_type
    assert queued.target == pawn.tile_pos


def test_apply_orders_sends_an_unknown_npc_id_to_the_first_npc(build_map: MapBuilder) -> None:
    npcs = make_npcs(build_map)
    order = NpcOrder(npc_id=-1, npc_name="Ghost", action_type=ActionType.EAT, voice_line="Hm")

    [outcome] = apply_orders(npcs, [order])

    assert outcome.is_accepted
    assert npcs[0]._speech_text == "Hm"


def test_apply_orders_drops_orders_when_there_is_no_npc() -> None:
    order = NpcOrder(npc_id=1, npc_name="Bob", action_type=ActionType.EAT, voice_line="Hm")

    assert apply_orders([], [order]) == []


def test_apply_orders_speaks_at_most_the_allowed_number_of_accepted_lines(
    build_map: MapBuilder,
) -> None:
    pawn, archer = make_npcs(build_map)
    orders = [
        make_order(archer, ActionType.CHOP_WOOD),
        make_order(pawn, ActionType.EAT),
        make_order(archer, ActionType.DEFEND),
    ]

    outcomes = apply_orders([pawn, archer], orders)

    spoken = [outcome.order for outcome in outcomes if outcome.is_spoken]
    assert spoken == orders[1:][:TTS_MAX_SPEAKERS]
    assert all(outcome.is_accepted for outcome in outcomes if outcome.is_spoken)
