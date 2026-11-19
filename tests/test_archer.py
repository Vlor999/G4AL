"""Archer combat planning on hand-built worlds: shoot, chase, defend."""

from collections.abc import Callable

import pytest

from game.actions import Action, ActionType, State
from game.archer import Archer
from game.arrows import Arrow
from game.fauna import Fauna, remove_dead_fauna
from game.map import GameMap
from game.settings import ARCHER_ARROW_DAMAGE, ARCHER_ARROW_FLIGHT, ARCHER_RANGE
from game.sheep import Sheep
from game.storage import ResourceStorage
from game.wild_archer import WildArcher
from tests.conftest import MapBuilder

FIELD = [".........."] * 4
# The enemy stands in the middle of a lake: no tile within range is walkable.
LAKE_FIELD = ["......~~~~", "......~~~~", "......~~~~", "......~~~~"]
# The enemy stands on an island: tiles within range exist but no path reaches them.
ISLAND_FIELD = ["......~~~~", "......~...", "......~...", "......~~~~"]

MAX_FRAMES = 5000


class Battlefield:
    """An archer at tile (0, 1) and the fauna and arrows lists it shares."""

    def __init__(self, game_map: GameMap) -> None:
        self.game_map = game_map
        self.fauna: list[Fauna] = []
        self.arrows: list[Arrow] = []
        self.archer = Archer(*game_map.tile_center(0, 1), game_map, [], ResourceStorage())
        self.archer.link_battlefield(fauna=self.fauna, arrows=self.arrows)

    def add_enemy(self, tile: tuple[int, int]) -> WildArcher:
        enemy = WildArcher(*self.game_map.tile_center(*tile), self.game_map, [])
        self.fauna.append(enemy)
        return enemy

    def run_until(self, is_reached: Callable[[], bool], max_frames: int = MAX_FRAMES) -> bool:
        for _ in range(max_frames):
            if is_reached():
                return True
            self.archer.update()
        return is_reached()

    def distance_to(self, enemy: Fauna) -> int:
        (archer_col, archer_row), (enemy_col, enemy_row) = self.archer.tile_pos, enemy.tile_pos
        return abs(archer_col - enemy_col) + abs(archer_row - enemy_row)


def move_enemy(battlefield: Battlefield, enemy: Fauna, tile: tuple[int, int]) -> None:
    enemy.x, enemy.y = battlefield.game_map.tile_center(*tile)


@pytest.mark.parametrize("enemy_tile", [(1, 1), (6, 2)], ids=["in-range", "out-of-range"])
def test_shoot_walks_into_range_and_fires_until_the_enemy_falls(
    build_map: MapBuilder, enemy_tile: tuple[int, int]
) -> None:
    battlefield = Battlefield(build_map(FIELD))
    enemy = battlefield.add_enemy(enemy_tile)
    starting_health = enemy.health

    battlefield.archer.enqueue(Action(ActionType.SHOOT))

    assert battlefield.run_until(lambda: len(battlefield.arrows) == 1)
    assert enemy.health == starting_health - ARCHER_ARROW_DAMAGE
    assert battlefield.arrows[0] == {
        "fromX": battlefield.archer.x,
        "fromY": battlefield.archer.y - 20,
        "toX": enemy.x,
        "toY": enemy.y - 10,
        "frame": 0,
        "totalFrames": ARCHER_ARROW_FLIGHT,
        "team": "blue",
    }
    assert battlefield.distance_to(enemy) <= ARCHER_RANGE
    assert battlefield.run_until(lambda: battlefield.archer.state == State.IDLE)
    assert enemy.health <= 0
    assert len(battlefield.arrows) == -(-starting_health // ARCHER_ARROW_DAMAGE)


def no_fauna(battlefield: Battlefield) -> None:
    pass


def only_a_sheep(battlefield: Battlefield) -> None:
    battlefield.fauna.append(
        Sheep(*battlefield.game_map.tile_center(1, 1), battlefield.game_map, [])
    )


def a_dead_enemy(battlefield: Battlefield) -> None:
    battlefield.add_enemy((1, 1)).health = 0


@pytest.mark.parametrize(
    ("rows", "place_fauna"),
    [
        (FIELD, no_fauna),
        (FIELD, only_a_sheep),
        (FIELD, a_dead_enemy),
        (LAKE_FIELD, lambda battlefield: battlefield.add_enemy((8, 1))),
        (ISLAND_FIELD, lambda battlefield: battlefield.add_enemy((8, 1))),
    ],
    ids=["no-fauna", "only-a-sheep", "dead-enemy", "enemy-in-a-lake", "enemy-on-an-island"],
)
def test_shoot_ends_at_once_without_a_reachable_living_enemy(
    build_map: MapBuilder, rows: list[str], place_fauna: Callable[[Battlefield], object]
) -> None:
    battlefield = Battlefield(build_map(rows))
    place_fauna(battlefield)

    battlefield.archer.enqueue(Action(ActionType.SHOOT))

    assert battlefield.archer.state == State.DONE
    assert battlefield.run_until(lambda: battlefield.archer.state == State.IDLE)
    assert battlefield.arrows == []


def test_an_enemy_killed_before_the_shot_stops_the_archer(build_map: MapBuilder) -> None:
    battlefield = Battlefield(build_map(FIELD))
    enemy = battlefield.add_enemy((1, 1))
    battlefield.archer.enqueue(Action(ActionType.SHOOT))
    battlefield.archer.update()

    enemy.health = 0

    assert battlefield.run_until(lambda: battlefield.archer.state == State.IDLE)
    assert battlefield.arrows == []


def test_an_enemy_killed_while_the_archer_walks_stops_it_on_arrival(
    build_map: MapBuilder,
) -> None:
    battlefield = Battlefield(build_map(FIELD))
    enemy = battlefield.add_enemy((6, 1))
    battlefield.archer.enqueue(Action(ActionType.SHOOT))
    assert battlefield.archer.state == State.MOVING

    enemy.health = 0

    assert battlefield.run_until(lambda: battlefield.archer.state == State.IDLE)
    assert battlefield.arrows == []


def test_the_archer_follows_an_enemy_that_moved_away_during_the_walk(
    build_map: MapBuilder,
) -> None:
    battlefield = Battlefield(build_map(FIELD))
    enemy = battlefield.add_enemy((4, 1))
    battlefield.archer.enqueue(Action(ActionType.SHOOT))

    move_enemy(battlefield, enemy, (9, 3))

    assert battlefield.run_until(lambda: len(battlefield.arrows) == 1)
    assert battlefield.distance_to(enemy) <= ARCHER_RANGE


def test_the_archer_follows_an_enemy_that_moved_away_between_two_shots(
    build_map: MapBuilder,
) -> None:
    battlefield = Battlefield(build_map(FIELD))
    enemy = battlefield.add_enemy((1, 1))
    battlefield.archer.enqueue(Action(ActionType.SHOOT))
    assert battlefield.run_until(lambda: len(battlefield.arrows) == 1)

    move_enemy(battlefield, enemy, (7, 3))

    assert battlefield.run_until(lambda: len(battlefield.arrows) == 2)
    assert battlefield.distance_to(enemy) <= ARCHER_RANGE


def test_defend_engages_every_enemy_in_its_radius_and_keeps_watching(
    build_map: MapBuilder,
) -> None:
    battlefield = Battlefield(build_map(FIELD))
    first = battlefield.add_enemy((1, 1))
    second = battlefield.add_enemy((4, 2))

    battlefield.archer.enqueue(Action(ActionType.DEFEND))

    assert battlefield.run_until(lambda: first.health <= 0 and second.health <= 0)
    assert battlefield.run_until(lambda: battlefield.archer.state == State.IDLE)
    newcomer = battlefield.add_enemy((3, 3))
    assert battlefield.run_until(lambda: newcomer.health <= 0)


def test_defend_ignores_an_enemy_beyond_its_radius(build_map: MapBuilder) -> None:
    battlefield = Battlefield(build_map(FIELD))
    battlefield.add_enemy((9, 3))

    battlefield.archer.enqueue(Action(ActionType.DEFEND))

    assert battlefield.archer.state == State.IDLE
    battlefield.run_until(lambda: False, max_frames=100)
    assert battlefield.archer.tile_pos == (0, 1)
    assert battlefield.arrows == []


def test_defend_switches_to_the_next_enemy_when_its_target_dies_before_the_shot(
    build_map: MapBuilder,
) -> None:
    battlefield = Battlefield(build_map(FIELD))
    first = battlefield.add_enemy((1, 1))
    battlefield.archer.enqueue(Action(ActionType.DEFEND))
    battlefield.archer.update()
    second = battlefield.add_enemy((3, 1))

    first.health = 0

    assert battlefield.run_until(lambda: len(battlefield.arrows) == 1)
    assert second.health < second.max_health


def test_defend_switches_to_the_next_enemy_when_its_target_dies_during_the_walk(
    build_map: MapBuilder,
) -> None:
    battlefield = Battlefield(build_map(FIELD))
    first = battlefield.add_enemy((5, 1))
    battlefield.archer.enqueue(Action(ActionType.DEFEND))
    assert battlefield.archer.state == State.MOVING
    second = battlefield.add_enemy((2, 3))

    first.health = 0

    assert battlefield.run_until(lambda: len(battlefield.arrows) == 1)
    assert second.health < second.max_health


def test_a_new_order_ends_defend_mode(build_map: MapBuilder) -> None:
    battlefield = Battlefield(build_map(FIELD))
    battlefield.archer.enqueue(Action(ActionType.DEFEND))

    battlefield.archer.enqueue(Action(ActionType.MOVE_TO, target=(2, 1)))
    assert battlefield.run_until(lambda: battlefield.archer.state == State.IDLE)
    battlefield.add_enemy((3, 1))

    battlefield.run_until(lambda: False, max_frames=200)
    assert battlefield.archer.tile_pos == (2, 1)
    assert battlefield.arrows == []


def test_the_archer_shoots_an_enemy_added_after_the_dead_were_removed(
    build_map: MapBuilder,
) -> None:
    battlefield = Battlefield(build_map(FIELD))
    battlefield.add_enemy((1, 1)).health = 0
    remove_dead_fauna(battlefield.fauna)
    newcomer = battlefield.add_enemy((2, 1))

    battlefield.archer.enqueue(Action(ActionType.SHOOT))

    assert battlefield.run_until(lambda: len(battlefield.arrows) == 1)
    assert newcomer.health == newcomer.max_health - ARCHER_ARROW_DAMAGE
