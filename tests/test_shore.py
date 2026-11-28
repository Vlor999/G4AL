import pytest

from game.world.shore import ShoreSpot, find_shore_spot
from tests.conftest import MapBuilder

Tile = tuple[int, int]


@pytest.mark.parametrize(
    ("rows", "start", "blocked", "expected"),
    [
        (["....~"], (0, 0), set(), ShoreSpot(shore_tile=(3, 0), water_tile=(4, 0))),
        (["~...."], (1, 0), set(), ShoreSpot(shore_tile=(1, 0), water_tile=(0, 0))),
        (
            ["~....", "....."],
            (2, 0),
            {(1, 0)},
            ShoreSpot(shore_tile=(0, 1), water_tile=(0, 0)),
        ),
        (["....."], (0, 0), set(), None),
        (["...~"], (0, 0), {(1, 0)}, None),
    ],
    ids=[
        "walks-to-the-water",
        "already-on-the-shore",
        "resource-on-the-shore",
        "no-water",
        "walled-in",
    ],
)
def test_find_shore_spot_returns_the_nearest_reachable_tile_next_to_water(
    build_map: MapBuilder,
    rows: list[str],
    start: Tile,
    blocked: set[Tile],
    expected: ShoreSpot | None,
) -> None:
    assert find_shore_spot(build_map(rows), start, blocked=blocked) == expected
