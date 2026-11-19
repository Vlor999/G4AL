"""Wild archer combat on hand-built worlds: target pick, approach, fire."""

import random
from collections.abc import Callable

from game.arrows import Arrow
from game.fauna import FaunaState
from game.map import GameMap
from game.npc import NPC
from game.settings import ARCHER_ARROW_FLIGHT, WILD_ARCHER_DAMAGE
from game.storage import ResourceStorage
from game.wild_archer import WildArcher
from tests.conftest import MapBuilder

FIELD = ["." * 10] * 4
MAX_FRAMES = 3000


class Ambush:
    """A wild archer and the pawns and arrows lists it shares."""

    def __init__(self, game_map: GameMap, archer_tile: tuple[int, int]) -> None:
        random.seed(3)
        self.game_map = game_map
        self.pawns: list[NPC] = []
        self.arrows: list[Arrow] = []
        self.archer = WildArcher(*game_map.tile_center(*archer_tile), game_map, [])
        self.archer.link_battlefield(npcs=self.pawns, arrows=self.arrows)

    def add_pawn(self, tile: tuple[int, int]) -> NPC:
        pawn = NPC(*self.game_map.tile_center(*tile), self.game_map, [], ResourceStorage())
        self.pawns.append(pawn)
        return pawn

    def run_until(self, is_reached: Callable[[], bool]) -> bool:
        for _ in range(MAX_FRAMES):
            if is_reached():
                return True
            self.archer.update()
        return is_reached()


def test_the_wild_archer_shoots_the_nearest_living_pawn(build_map: MapBuilder) -> None:
    ambush = Ambush(build_map(FIELD), (1, 1))
    ambush.add_pawn((0, 1)).health = 0
    nearest = ambush.add_pawn((2, 1))
    farther = ambush.add_pawn((6, 1))

    assert ambush.run_until(lambda: len(ambush.arrows) == 1)

    assert nearest.health == nearest.max_health - WILD_ARCHER_DAMAGE
    assert farther.health == farther.max_health


def test_the_wild_archer_approaches_a_pawn_and_fires_red_arrows(build_map: MapBuilder) -> None:
    ambush = Ambush(build_map(FIELD), (5, 1))
    pawn = ambush.add_pawn((0, 1))

    assert ambush.run_until(lambda: len(ambush.arrows) == 1)

    assert ambush.arrows[0] == {
        "fromX": ambush.archer.x,
        "fromY": ambush.archer.y - 20,
        "toX": pawn.x,
        "toY": pawn.y - 10,
        "frame": 0,
        "totalFrames": ARCHER_ARROW_FLIGHT,
        "team": "red",
    }
    assert ambush.run_until(lambda: len(ambush.arrows) == 2)
    assert pawn.health == pawn.max_health - 2 * WILD_ARCHER_DAMAGE


def test_a_pawn_leaving_range_before_the_shot_stops_the_wild_archer(
    build_map: MapBuilder,
) -> None:
    ambush = Ambush(build_map(FIELD), (1, 1))
    pawn = ambush.add_pawn((2, 1))
    assert ambush.run_until(lambda: ambush.archer.state == FaunaState.SHOOTING)

    pawn.x, pawn.y = ambush.game_map.tile_center(9, 3)

    assert ambush.run_until(lambda: ambush.archer.state == FaunaState.IDLE)
    assert ambush.arrows == []
    assert pawn.health == pawn.max_health


def test_a_pawn_dying_before_the_shot_stops_the_wild_archer(build_map: MapBuilder) -> None:
    ambush = Ambush(build_map(FIELD), (1, 1))
    pawn = ambush.add_pawn((2, 1))
    assert ambush.run_until(lambda: ambush.archer.state == FaunaState.SHOOTING)

    pawn.health = 0
    ambush.archer.update()

    assert ambush.archer.state == FaunaState.IDLE
    assert ambush.arrows == []


def test_a_dead_wild_archer_does_nothing(build_map: MapBuilder) -> None:
    ambush = Ambush(build_map(FIELD), (1, 1))
    pawn = ambush.add_pawn((2, 1))
    ambush.archer.health = 0

    ambush.run_until(lambda: False)

    assert ambush.arrows == []
    assert pawn.health == pawn.max_health
