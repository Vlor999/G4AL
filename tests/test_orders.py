import pytest

from game.actions import ActionType, State
from game.archer import Archer
from game.npc import NPC
from game.orders import NpcOrder, OrderOutcome, apply_orders
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
    npcs.append(NPC(pawn_x, pawn_y, game_map, [], storage, name="Bob"))
    npcs.append(Archer(archer_x, archer_y, game_map, [], storage, name="Robin"))
    return npcs


def make_order(npc: NPC, action_type: ActionType) -> NpcOrder:
    return NpcOrder(npc_id=npc.id, npc_name=npc.name, action_type=action_type, voice_line="On it!")


@pytest.mark.parametrize(
    ("archer_action", "expected_accepted"),
    [(ActionType.DEFEND, True), (ActionType.CHOP_WOOD, False)],
)
def test_apply_orders_reports_whether_the_npc_took_the_action(
    build_map: MapBuilder, archer_action: ActionType, expected_accepted: bool
) -> None:
    archer = make_npcs(build_map)[1]

    [outcome] = apply_orders([archer], [make_order(archer, archer_action)])

    assert outcome.is_accepted is expected_accepted
    assert (archer.visible_speech_text == "On it!") is expected_accepted


def test_apply_orders_aims_a_build_order_at_the_npc_tile(build_map: MapBuilder) -> None:
    pawn = make_npcs(build_map)[0]
    # A busy NPC only queues the action, so the test reads it before it starts.
    pawn.state = State.MOVING

    apply_orders([pawn], [make_order(pawn, ActionType.BUILD)])

    [queued] = pawn.action_queue
    assert queued.target == pawn.tile_pos


def test_voice_order_cannot_be_a_move_to_without_target() -> None:
    with pytest.raises(ValueError, match="move_to needs a target tile"):
        NpcOrder(npc_id=1, npc_name="Bob", action_type=ActionType.MOVE_TO, voice_line="Going!")


@pytest.mark.parametrize("has_npcs", [True, False], ids=["other-npcs", "no-npc"])
def test_apply_orders_does_not_accept_an_order_for_an_unknown_npc_id(
    build_map: MapBuilder, has_npcs: bool
) -> None:
    npcs = make_npcs(build_map) if has_npcs else []
    order = NpcOrder(npc_id=-1, npc_name="Ghost", action_type=ActionType.EAT, voice_line="Hm")

    outcomes = apply_orders(npcs, [order])

    assert outcomes == [OrderOutcome(order, is_accepted=False, is_spoken=False)]
    assert all(npc.queue_size == 0 and npc.visible_speech_text != "Hm" for npc in npcs)


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
