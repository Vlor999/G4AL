"""Lake actions on hand-built worlds: go to the shore, fish, swim."""

from dataclasses import dataclass

import pytest

from game.npcs.actions import REFUSAL_SPEECH, Action, ActionRefusal, ActionType, State
from game.npcs.archer import Archer
from game.npcs.npc import NPC
from game.resources.entities import Tree
from game.resources.storage import ResourceStorage
from game.settings import (
    NPC_FISH_RESTORE,
    NPC_FISH_TIME,
    NPC_HUNGER_DRAIN,
    NPC_SWIM_TIME,
    STORAGE_BASE_CAPACITY,
)
from tests.conftest import MapBuilder

# A lake fills the two east columns; the NPC starts at (0, 1), the shore is (5, 1).
LAKE_FIELD = ["......~~", "......~~", "......~~"]
DRY_FIELD = ["........"] * 3
START = (0, 1)
SHORE_TILE = (5, 1)
WATER_TILE = (6, 1)
MAX_FRAMES = 3000


@dataclass(frozen=True)
class Frame:
    """What one ``update`` left the NPC doing."""

    tile: tuple[int, int]
    state: State
    is_in_water: bool


def make_npc(build_map: MapBuilder, npc_class: type[NPC], rows: list[str]) -> NPC:
    game_map = build_map(rows)
    return npc_class(*game_map.tile_center(*START), game_map, [], ResourceStorage(), name="Bob")


def run_until_idle(npc: NPC) -> list[Frame]:
    frames: list[Frame] = []
    for _ in range(MAX_FRAMES):
        if npc.state == State.IDLE:
            return frames
        npc.update()
        frames.append(Frame(npc.tile_pos, npc.state, npc.is_in_water))
    raise AssertionError(f"the action did not end in {MAX_FRAMES} frames")


def count_performing(frames: list[Frame]) -> int:
    return sum(frame.state == State.PERFORMING for frame in frames)


@pytest.mark.parametrize(
    ("npc_class", "action_type", "is_accepted"),
    [
        (NPC, ActionType.GO_TO_SHORE, True),
        (NPC, ActionType.FISH, True),
        (NPC, ActionType.SWIM, True),
        (Archer, ActionType.GO_TO_SHORE, True),
        (Archer, ActionType.FISH, False),
        (Archer, ActionType.SWIM, True),
    ],
)
def test_each_npc_kind_accepts_only_its_lake_actions(
    build_map: MapBuilder, npc_class: type[NPC], action_type: ActionType, is_accepted: bool
) -> None:
    npc = make_npc(build_map, npc_class, LAKE_FIELD)

    assert npc.enqueue(Action(action_type)) is is_accepted


@pytest.mark.parametrize(
    ("npc_class", "action_type"),
    [
        (NPC, ActionType.GO_TO_SHORE),
        (NPC, ActionType.FISH),
        (NPC, ActionType.SWIM),
        (Archer, ActionType.GO_TO_SHORE),
        (Archer, ActionType.SWIM),
    ],
)
def test_a_lake_action_without_a_reachable_shore_is_refused_with_its_reason(
    build_map: MapBuilder, npc_class: type[NPC], action_type: ActionType
) -> None:
    npc = make_npc(build_map, npc_class, DRY_FIELD)

    npc.enqueue(Action(action_type))

    assert npc.state == State.DONE
    assert npc.last_refusal is ActionRefusal.NO_SHORE_REACHABLE
    assert npc.visible_speech_text == REFUSAL_SPEECH[ActionRefusal.NO_SHORE_REACHABLE]


def test_the_refusal_lasts_until_the_next_action_ends(build_map: MapBuilder) -> None:
    npc = make_npc(build_map, NPC, DRY_FIELD)

    npc.enqueue(Action(ActionType.FISH))
    npc.enqueue(Action(ActionType.MOVE_TO, target=(3, 1)))

    assert npc.state == State.MOVING
    assert npc.last_refusal is ActionRefusal.NO_SHORE_REACHABLE
    run_until_idle(npc)
    assert npc.last_refusal is None


def make_refused_woodcutter(build_map: MapBuilder, storage: ResourceStorage) -> NPC:
    """A pawn on a dry map whose ``fish`` was refused, then sent to chop a one-wood tree."""
    game_map = build_map(DRY_FIELD)
    tree = Tree(1, 1)
    tree.remaining_yields = {"wood": 1}
    npc = NPC(*game_map.tile_center(*START), game_map, [tree], storage, name="Bob")
    npc.enqueue(Action(ActionType.FISH))
    npc.enqueue(Action(ActionType.CHOP_WOOD))
    return npc


def test_the_refusal_ends_with_a_harvest_that_ends_at_the_hut(build_map: MapBuilder) -> None:
    npc = make_refused_woodcutter(build_map, ResourceStorage())
    npc.enqueue(Action(ActionType.MOVE_TO, target=(3, 1)))

    for _ in range(MAX_FRAMES):
        if npc.current_action_type == ActionType.MOVE_TO:
            break
        npc.update()

    assert npc.current_action_type == ActionType.MOVE_TO
    assert npc.last_refusal is None


def test_the_refusal_ends_when_the_npc_gives_up_a_waiting_deposit(
    build_map: MapBuilder,
) -> None:
    storage = ResourceStorage()
    storage.add("stone", STORAGE_BASE_CAPACITY)
    npc = make_refused_woodcutter(build_map, storage)
    for _ in range(MAX_FRAMES):
        if npc.state == State.WAITING_DEPOSIT:
            break
        npc.update()

    assert npc.give_up_waiting_deposit()
    assert npc.last_refusal is None


def test_a_new_action_does_not_keep_the_water_tile_of_the_last_one(
    build_map: MapBuilder,
) -> None:
    npc = make_npc(build_map, NPC, LAKE_FIELD)
    npc.enqueue(Action(ActionType.GO_TO_SHORE))
    run_until_idle(npc)
    npc.enqueue(Action(ActionType.SWIM))
    for _ in range(MAX_FRAMES):
        if npc.state == State.DONE:
            break
        npc.update()

    npc.enqueue(Action(ActionType.MOVE_TO, target=(0, 0)))

    assert npc.water_tile is None


@pytest.mark.parametrize("npc_class", [NPC, Archer])
def test_go_to_shore_stops_on_the_shore_tile_without_entering_the_water(
    build_map: MapBuilder, npc_class: type[NPC]
) -> None:
    npc = make_npc(build_map, npc_class, LAKE_FIELD)

    npc.enqueue(Action(ActionType.GO_TO_SHORE))

    assert npc.water_tile == WATER_TILE
    frames = run_until_idle(npc)
    assert npc.tile_pos == SHORE_TILE
    assert not any(frame.is_in_water for frame in frames)
    assert npc.water_tile is None


def test_fishing_refills_hunger_by_its_amount_after_its_duration(build_map: MapBuilder) -> None:
    npc = make_npc(build_map, NPC, LAKE_FIELD)
    npc.hunger = 10.0

    npc.enqueue(Action(ActionType.FISH))
    frames = run_until_idle(npc)

    assert count_performing(frames) == NPC_FISH_TIME
    assert npc.tile_pos == SHORE_TILE
    assert not any(frame.is_in_water for frame in frames)
    expected_hunger = 10.0 - len(frames) * NPC_HUNGER_DRAIN + NPC_FISH_RESTORE
    assert npc.hunger == pytest.approx(expected_hunger)


@pytest.mark.parametrize("npc_class", [NPC, Archer])
def test_swimming_enters_one_water_tile_and_comes_back_to_the_shore_tile(
    build_map: MapBuilder, npc_class: type[NPC]
) -> None:
    npc = make_npc(build_map, npc_class, LAKE_FIELD)

    npc.enqueue(Action(ActionType.SWIM))
    frames = run_until_idle(npc)

    assert {frame.tile for frame in frames if frame.is_in_water} == {WATER_TILE}
    assert count_performing(frames) == NPC_SWIM_TIME
    assert all(frame.is_in_water for frame in frames if frame.state == State.PERFORMING)
    assert npc.tile_pos == SHORE_TILE
    assert not npc.is_in_water
