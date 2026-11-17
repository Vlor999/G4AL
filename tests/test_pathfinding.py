import pytest

from game.pathfinding import find_path
from tests.conftest import MapBuilder


@pytest.mark.parametrize(
    ("rows", "goal", "expected"),
    [
        (["....."], (4, 0), [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]),
        (["..~.."], (4, 0), []),
        (["...~"], (3, 0), [(0, 0), (1, 0), (2, 0)]),
        ([".~~", "~~~", "~~~"], (2, 2), []),
    ],
    ids=["straight", "water-wall", "unwalkable-goal-moves-next-to-it", "goal-unreachable"],
)
def test_find_path(
    build_map: MapBuilder,
    rows: list[str],
    goal: tuple[int, int],
    expected: list[tuple[int, int]],
) -> None:
    assert find_path(build_map(rows), (0, 0), goal) == expected


def test_find_path_detours_around_blocked_tiles(build_map: MapBuilder) -> None:
    path = find_path(build_map(["...", "..."]), (0, 0), (2, 0), blocked={(1, 0)})
    assert path == [(0, 0), (0, 1), (1, 1), (2, 1), (2, 0)]


def test_find_path_never_treats_goal_as_blocked(build_map: MapBuilder) -> None:
    path = find_path(build_map(["..."]), (0, 0), (2, 0), blocked={(2, 0)})
    assert path == [(0, 0), (1, 0), (2, 0)]
