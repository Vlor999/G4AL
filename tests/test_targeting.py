from dataclasses import dataclass

import pytest

from game.combat.targeting import find_nearest_living


@dataclass
class Target:
    name: str
    tile_pos: tuple[int, int]
    health: float = 10.0


@pytest.mark.parametrize(
    ("targets", "max_distance", "expected"),
    [
        ([Target("far", (5, 0)), Target("near", (2, 0))], None, "near"),
        ([Target("first", (0, 3)), Target("second", (3, 0))], None, "first"),
        ([Target("dead", (1, 0), health=0), Target("alive", (4, 0))], None, "alive"),
        ([Target("near", (3, 0)), Target("far", (4, 0))], 3, "near"),
        ([Target("far", (4, 0))], 3, None),
        ([], None, None),
    ],
    ids=["nearest", "earliest-wins-a-tie", "dead-skipped", "within-bound", "beyond-bound", "none"],
)
def test_find_nearest_living(
    targets: list[Target], max_distance: int | None, expected: str | None
) -> None:
    nearest = find_nearest_living((0, 0), targets, max_distance=max_distance)

    assert (nearest.name if nearest else None) == expected
