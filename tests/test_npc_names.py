from collections import Counter
from collections.abc import Callable

import pytest

from game.creatures import WildArcher
from game.npc_names import NPC_NAMES, pick_archer_name, pick_npc_name
from tests.conftest import MapBuilder

ARCHER_NAMES = ("Robin", "Artemis", "Hawke", "Fletcher", "Ygritte", "Legolas")
WILD_ARCHER_NAMES = ("Bandit", "Outlaw", "Rogue", "Poacher", "Marauder", "Raider")


def test_npc_names_keep_their_content_and_pick_order() -> None:
    assert NPC_NAMES == ("Bob", "Paul", "Thomas", "Marie", "Sam", "Lisa")


def pick_wild_archer_name(build_map: MapBuilder) -> Callable[[], str]:
    game_map = build_map(["."])
    return lambda: WildArcher(0.0, 0.0, game_map, []).name


@pytest.mark.parametrize(
    ("make_picker", "pool"),
    [
        (lambda build_map: pick_npc_name, NPC_NAMES),
        (lambda build_map: pick_archer_name, ARCHER_NAMES),
        (pick_wild_archer_name, WILD_ARCHER_NAMES),
    ],
    ids=["pawn", "archer", "wild-archer"],
)
def test_a_name_comes_back_only_once_its_whole_pool_was_picked(
    build_map: MapBuilder,
    make_picker: Callable[[MapBuilder], Callable[[], str]],
    pool: tuple[str, ...],
) -> None:
    pick = make_picker(build_map)

    picks = Counter(pick() for _ in range(3 * len(pool)))

    # Earlier tests may have used part of the pool: the first cycle can be short.
    assert set(picks) == set(pool)
    assert set(picks.values()) <= {2, 3, 4}
