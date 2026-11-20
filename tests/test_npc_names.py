import random
from collections import Counter
from collections.abc import Callable

import pytest

from game.archer import Archer
from game.map import GameMap
from game.npc import NPC
from game.npc_names import (
    ARCHER_NAMES,
    NPC_NAMES,
    WILD_ARCHER_NAMES,
    NamePool,
    NamePools,
)
from game.storage import ResourceStorage
from game.wild_archer import WildArcher
from tests.conftest import MapBuilder


def test_npc_names_keep_their_content_and_pick_order() -> None:
    assert NPC_NAMES == ("Bob", "Paul", "Thomas", "Marie", "Sam", "Lisa")


@pytest.mark.parametrize(
    ("pool_of", "names"),
    [
        (lambda pools: pools.pawns, NPC_NAMES),
        (lambda pools: pools.archers, ARCHER_NAMES),
        (lambda pools: pools.wild_archers, WILD_ARCHER_NAMES),
    ],
    ids=["pawn", "archer", "wild-archer"],
)
def test_a_name_comes_back_only_once_its_whole_pool_was_picked(
    pool_of: Callable[[NamePools], NamePool], names: tuple[str, ...]
) -> None:
    pool = pool_of(NamePools(random.Random(0)))

    picks = Counter(pool.pick() for _ in range(3 * len(names)))

    assert picks == Counter(dict.fromkeys(names, 3))


@pytest.mark.parametrize(
    ("names", "seeded_picks"),
    [
        (NPC_NAMES, ["Marie", "Lisa", "Sam", "Paul", "Bob", "Thomas", "Sam"]),
        (ARCHER_NAMES, ["Fletcher", "Legolas", "Ygritte", "Artemis", "Robin", "Hawke", "Ygritte"]),
        (
            WILD_ARCHER_NAMES,
            ["Poacher", "Raider", "Marauder", "Outlaw", "Bandit", "Rogue", "Marauder"],
        ),
    ],
    ids=["pawn", "archer", "wild-archer"],
)
def test_a_fresh_pool_picks_names_in_seeded_order(
    names: tuple[str, ...], seeded_picks: list[str]
) -> None:
    pool = NamePool(names, rng=random.Random(11))

    assert [pool.pick() for _ in range(len(names) + 1)] == seeded_picks


@pytest.mark.parametrize(
    ("build_npc", "names"),
    [
        (lambda game_map: NPC(0.0, 0.0, game_map, [], ResourceStorage()).name, NPC_NAMES),
        (lambda game_map: Archer(0.0, 0.0, game_map, [], ResourceStorage()).name, ARCHER_NAMES),
        (lambda game_map: WildArcher(0.0, 0.0, game_map, []).name, WILD_ARCHER_NAMES),
    ],
    ids=["pawn", "archer", "wild-archer"],
)
def test_a_new_npc_takes_the_next_name_of_its_map_pool(
    build_map: MapBuilder, build_npc: Callable[[GameMap], str], names: tuple[str, ...]
) -> None:
    game_map = build_map(["."])

    picks = [build_npc(game_map) for _ in names]

    assert sorted(picks) == sorted(names)
