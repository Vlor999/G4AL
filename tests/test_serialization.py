"""The resource, NPC and fauna fields of the state payload the client reads (`docs/api.md`)."""

from typing import Any

from game.actions import Action, ActionType
from game.archer import Archer
from game.arrows import Arrow
from game.entities import Structure
from game.fauna import Fauna
from game.map import GameMap
from game.npc import NPC
from game.sheep import Sheep
from game.storage import ResourceStorage
from game.wild_archer import WildArcher
from server.serialization import serialize_state
from tests.conftest import MapBuilder

FIELD = ["......"] * 4
MAX_FRAMES = 1000


def serialize(game_map: GameMap, *, npcs: list[NPC], fauna: list[Fauna]) -> dict[str, Any]:
    return serialize_state(
        game_map=game_map,
        resources=[],
        npcs=npcs,
        fauna=fauna,
        arrows=[],
        storage=ResourceStorage(),
        log_messages=[],
    )


def test_an_idle_pawn_shows_no_action_no_speech_and_no_combat(build_map: MapBuilder) -> None:
    game_map = build_map(FIELD)
    pawn = NPC(*game_map.tile_center(0, 0), game_map, [], ResourceStorage())

    [npc_state] = serialize(game_map, npcs=[pawn], fauna=[])["npcs"]

    assert (
        npc_state["actionType"],
        npc_state["speechText"],
        npc_state["isFiring"],
        npc_state["isDefending"],
    ) == ("", "", False, False)


def test_a_pawn_on_an_order_shows_its_action_type(build_map: MapBuilder) -> None:
    game_map = build_map(FIELD)
    pawn = NPC(*game_map.tile_center(0, 0), game_map, [], ResourceStorage())
    pawn.enqueue(Action(ActionType.MOVE_TO, target=(4, 2)))

    [npc_state] = serialize(game_map, npcs=[pawn], fauna=[])["npcs"]

    assert (npc_state["actionType"], npc_state["isFiring"], npc_state["isDefending"]) == (
        "move_to",
        False,
        False,
    )


def test_a_speech_bubble_shows_until_its_duration_runs_out(build_map: MapBuilder) -> None:
    game_map = build_map(FIELD)
    pawn = NPC(*game_map.tile_center(0, 0), game_map, [], ResourceStorage())
    pawn.say("Hello", 2)

    shown = serialize(game_map, npcs=[pawn], fauna=[])["npcs"][0]["speechText"]
    pawn.update()
    pawn.update()
    hidden = serialize(game_map, npcs=[pawn], fauna=[])["npcs"][0]["speechText"]

    assert (shown, hidden) == ("Hello", "")


def test_a_defending_archer_shows_its_action_and_its_shot(build_map: MapBuilder) -> None:
    game_map = build_map(FIELD)
    fauna: list[Fauna] = [WildArcher(*game_map.tile_center(2, 1), game_map, [])]
    arrows: list[Arrow] = []
    archer = Archer(*game_map.tile_center(0, 1), game_map, [], ResourceStorage())
    archer.link_battlefield(fauna=fauna, arrows=arrows)
    archer.enqueue(Action(ActionType.DEFEND))
    for _ in range(MAX_FRAMES):
        if arrows:
            break
        archer.update()

    [npc_state] = serialize(game_map, npcs=[archer], fauna=[])["npcs"]

    assert (
        npc_state["actionType"],
        npc_state["speechText"],
        npc_state["isFiring"],
        npc_state["isDefending"],
    ) == ("defend", "Fire!", True, True)


def test_a_wild_archer_shows_its_shot_and_a_sheep_never_fires(build_map: MapBuilder) -> None:
    game_map = build_map(FIELD)
    pawn = NPC(*game_map.tile_center(0, 1), game_map, [], ResourceStorage())
    arrows: list[Arrow] = []
    wild_archer = WildArcher(*game_map.tile_center(2, 1), game_map, [])
    wild_archer.link_battlefield(npcs=[pawn], arrows=arrows)
    sheep = Sheep(*game_map.tile_center(5, 3), game_map, [])
    for _ in range(MAX_FRAMES):
        if arrows:
            break
        wild_archer.update()

    states = serialize(game_map, npcs=[], fauna=[wild_archer, sheep])["fauna"]

    assert [state["isFiring"] for state in states] == [True, False]


def test_resources_npcs_and_fauna_carry_their_footprint_height_and_sprite_box(
    build_map: MapBuilder,
) -> None:
    game_map = build_map(FIELD)
    pawn = NPC(*game_map.tile_center(0, 0), game_map, [], ResourceStorage())
    sheep = Sheep(*game_map.tile_center(5, 3), game_map, [])
    state = serialize_state(
        game_map=game_map,
        resources=[Structure(1, 1, building_type="storage_hut")],
        npcs=[pawn],
        fauna=[sheep],
        arrows=[],
        storage=ResourceStorage(),
        log_messages=[],
    )

    [hut], [pawn_state], [sheep_state] = state["resources"], state["npcs"], state["fauna"]
    assert (hut["footprint"], hut["height"]) == ({"width": 2, "depth": 2}, 1)
    assert hut["sprite"] == {"width": 2, "height": 3.0, "anchorX": 1.0, "anchorY": 3.0}
    assert pawn_state["sprite"] == {"width": 1.0, "height": 1.0, "anchorX": 0.5, "anchorY": 0.84375}
    assert sheep_state["footprint"] == {"width": 1, "depth": 1}
