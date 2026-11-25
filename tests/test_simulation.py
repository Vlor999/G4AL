"""One frame of the world on hand-built worlds: what each step does and their order."""

from collections.abc import Callable

import pytest

from game.combat.arrows import Arrow, Team, advance_arrows
from game.fauna.fauna import Fauna, FaunaState
from game.fauna.sheep import Sheep
from game.fauna.wild_archer import WildArcher
from game.npcs.actions import Action, ActionType
from game.npcs.archer import Archer
from game.npcs.npc import NPC
from game.resources.entities import Resource, WheatField
from game.resources.storage import ResourceStorage
from game.settings import NPC_HUNGER_DAMAGE, NPC_HUNGER_DRAIN, WILD_ARCHER_GRACE_FRAMES
from game.simulation import advance_world
from game.spawning import spawn_world
from game.world.clock import WorldClock
from game.world.map import GameMap
from tests.conftest import MapBuilder, clock_at

FIELD = ["......"] * 4
MAX_FRAMES = 1000


class World:
    """A hand-built world whose grace period is over."""

    def __init__(self, game_map: GameMap) -> None:
        self.game_map = game_map
        self.clock = clock_at(WILD_ARCHER_GRACE_FRAMES)
        self.npcs: list[NPC] = []
        self.fauna: list[Fauna] = []
        self.resources: list[Resource] = []
        self.arrows: list[Arrow] = []

    def add_pawn(self, tile: tuple[int, int]) -> NPC:
        pawn = NPC(*self.game_map.tile_center(*tile), self.game_map, [], ResourceStorage())
        self.npcs.append(pawn)
        return pawn

    def advance(self) -> None:
        advance_world(
            npcs=self.npcs,
            fauna=self.fauna,
            resources=self.resources,
            arrows=self.arrows,
            clock=self.clock,
        )

    def advance_until(self, is_reached: Callable[[], bool]) -> bool:
        for _ in range(MAX_FRAMES):
            if is_reached():
                return True
            self.advance()
        return is_reached()


def make_arrow(*, frame: int, total_frames: int) -> Arrow:
    return {
        "fromX": 0.0,
        "fromY": 0.0,
        "toX": 10.0,
        "toY": 10.0,
        "frame": frame,
        "totalFrames": total_frames,
        "team": Team.BLUE,
    }


@pytest.mark.parametrize(
    ("frame", "expected_frames"), [(0, [1]), (3, [4]), (4, [])], ids=["new", "flying", "landing"]
)
def test_advance_arrows_ages_each_arrow_and_drops_the_landed(
    frame: int, expected_frames: list[int]
) -> None:
    arrows = [make_arrow(frame=frame, total_frames=5)]

    advance_arrows(arrows)

    assert [arrow["frame"] for arrow in arrows] == expected_frames


class ClockWatcher(Sheep):
    """A sheep that records the elapsed frames it reads on the world clock each frame."""

    def __init__(self, game_map: GameMap, clock: WorldClock) -> None:
        super().__init__(*game_map.tile_center(4, 3), game_map, [])
        self.clock = clock
        self.elapsed_frames_read: list[int] = []

    def update(self) -> None:
        self.elapsed_frames_read.append(self.clock.elapsed_frames)


def test_the_world_clock_advances_once_at_the_end_of_each_frame(build_map: MapBuilder) -> None:
    world = World(build_map(FIELD))
    world.clock = WorldClock()
    watcher = ClockWatcher(world.game_map, world.clock)
    world.fauna.append(watcher)

    world.advance()
    world.advance()

    assert watcher.elapsed_frames_read == [0, 1]
    assert world.clock.elapsed_frames == 2


def test_a_frame_grows_wheat_and_removes_dead_fauna(build_map: MapBuilder) -> None:
    world = World(build_map(FIELD))
    field = WheatField(0, 0)
    world.resources.append(field)
    alive, dead = (Sheep(*world.game_map.tile_center(col, 3), world.game_map, []) for col in (4, 5))
    dead.health = 0
    world.fauna[:] = [alive, dead]

    world.advance()

    assert field.growth == 1
    assert world.fauna == [alive]


@pytest.mark.parametrize(
    ("is_dead_npc_selected", "expected_selected"),
    [(True, [0]), (False, [])],
    ids=["selected-npc-dies", "unselected-npc-dies"],
)
def test_dead_npcs_leave_and_the_selection_goes_to_the_first_survivor(
    build_map: MapBuilder, is_dead_npc_selected: bool, expected_selected: list[int]
) -> None:
    world = World(build_map(FIELD))
    world.add_pawn((0, 0))
    dead = world.add_pawn((1, 0))
    world.add_pawn((2, 0))
    dead.selected = is_dead_npc_selected
    dead.health = 0

    world.advance()

    assert dead not in world.npcs
    assert [index for index, npc in enumerate(world.npcs) if npc.selected] == expected_selected


def test_a_dead_npc_still_acts_in_its_last_frame(build_map: MapBuilder) -> None:
    world = World(build_map(FIELD))
    dead = world.add_pawn((0, 0))
    dead.health = 0

    world.advance()

    assert dead not in world.npcs
    assert dead.hunger == dead.max_hunger - NPC_HUNGER_DRAIN


def test_an_arrow_released_this_frame_is_aged_in_the_same_frame(build_map: MapBuilder) -> None:
    world = World(build_map(FIELD))
    archer = Archer(*world.game_map.tile_center(0, 1), world.game_map, [], ResourceStorage())
    world.npcs.append(archer)
    world.fauna.append(WildArcher(*world.game_map.tile_center(1, 1), world.game_map, []))
    archer.link_battlefield(fauna=world.fauna, arrows=world.arrows)
    archer.enqueue(Action(ActionType.SHOOT))

    assert world.advance_until(lambda: bool(world.arrows))

    assert [arrow["frame"] for arrow in world.arrows] == [1]


def test_npcs_act_before_fauna(build_map: MapBuilder) -> None:
    world = World(build_map(FIELD))
    pawn = world.add_pawn((0, 1))
    wild_archer = WildArcher(*world.game_map.tile_center(1, 1), world.game_map, [])
    wild_archer.link_battlefield(npcs=world.npcs, arrows=world.arrows, clock=world.clock)
    world.fauna.append(wild_archer)
    assert world.advance_until(lambda: wild_archer.state == FaunaState.SHOOTING)
    pawn.hunger = 0.0
    pawn.health = NPC_HUNGER_DAMAGE

    world.advance()

    assert pawn not in world.npcs
    assert wild_archer.state == FaunaState.IDLE
    assert world.arrows == []


REPLAY_FRAMES = 300
Snapshot = list[tuple[str, float, float]]


def play_seeded_game(seed: int) -> Snapshot:
    """Spawn a world from ``seed``, add new NPCs and creatures halfway, run it, and
    return the name and position of everyone left."""
    game_map = GameMap(seed=seed)
    world = spawn_world(game_map)
    for frame in range(REPLAY_FRAMES):
        if frame == REPLAY_FRAMES // 2:
            x, y = world.npcs[0].x, world.npcs[0].y
            world.npcs.append(NPC(x, y, game_map, world.resources, world.storage))
            world.npcs.append(Archer(x, y, game_map, world.resources, world.storage))
            world.fauna.append(Sheep(x, y, game_map, world.resources))
            world.fauna.append(WildArcher(x, y, game_map, world.resources))
        advance_world(
            npcs=world.npcs,
            fauna=world.fauna,
            resources=world.resources,
            arrows=world.arrows,
            clock=world.clock,
        )
    return [(being.name, being.x, being.y) for being in [*world.npcs, *world.fauna]]


@pytest.mark.parametrize("seed", [0, 42])
def test_the_same_seed_replays_the_same_positions_and_names(seed: int) -> None:
    assert play_seeded_game(seed) == play_seeded_game(seed)
