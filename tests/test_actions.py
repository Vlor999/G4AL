import pytest

from game.npcs.actions import ActionType, create_order_action

OWN_TILE = (1, 1)
TARGET = (2, 3)


@pytest.mark.parametrize(
    ("action_type", "target", "expected_target"),
    [
        (ActionType.BUILD, None, OWN_TILE),
        (ActionType.BUILD, TARGET, TARGET),
        (ActionType.PLANT_WHEAT, None, OWN_TILE),
        (ActionType.PLANT_WHEAT, TARGET, TARGET),
        (ActionType.MOVE_TO, TARGET, TARGET),
        (ActionType.CHOP_WOOD, None, None),
        (ActionType.CHOP_WOOD, TARGET, None),
    ],
)
def test_create_order_action_aims_build_and_plant_at_the_own_tile_without_target(
    action_type: ActionType,
    target: tuple[int, int] | None,
    expected_target: tuple[int, int] | None,
) -> None:
    action = create_order_action(action_type, target=target, own_tile=OWN_TILE)

    assert action.action_type is action_type
    assert action.target == expected_target
