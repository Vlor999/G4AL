"""The resource, NPC and fauna fields of the state payload the client reads (`docs/api.md`)."""

from typing import Any

import pytest

from game.combat.arrows import Arrow
from game.fauna.fauna import Fauna
from game.fauna.sheep import Sheep
from game.fauna.wild_archer import WildArcher
from game.npcs.actions import Action, ActionType
from game.npcs.archer import Archer
from game.npcs.npc import NPC
from game.resources.entities import Structure
from game.resources.storage import ResourceStorage
from game.settings import WILD_ARCHER_GRACE_FRAMES
from game.world.map import GameMap
from game.world.terrain import Biome
from server.model_selection import SelectedModel
from server.serialization import serialize_state
from tests.conftest import MapBuilder, clock_at
from tests.fakes import VOICE_MODEL, ScriptedOrderInterpreter

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
        chat_messages=[],
        available_models=[],
        selected_model=SelectedModel(
            model=VOICE_MODEL, text=ScriptedOrderInterpreter(), voice=None
        ),
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


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (["....~"], {"isInWater": False, "waterTile": [4, 0], "lastRefusal": None}),
        (FIELD, {"isInWater": False, "waterTile": None, "lastRefusal": "no shore reachable"}),
    ],
    ids=["lake-found", "no-lake"],
)
def test_a_pawn_sent_to_the_lake_shows_its_water_tile_or_its_refusal(
    build_map: MapBuilder, rows: list[str], expected: dict[str, Any]
) -> None:
    game_map = build_map(rows)
    pawn = NPC(*game_map.tile_center(0, 0), game_map, [], ResourceStorage())
    pawn.enqueue(Action(ActionType.SWIM))

    [npc_state] = serialize(game_map, npcs=[pawn], fauna=[])["npcs"]

    assert {key: npc_state[key] for key in expected} == expected


def test_a_pawn_in_the_lake_shows_it_is_in_water(build_map: MapBuilder) -> None:
    game_map = build_map(["~.."])
    pawn = NPC(*game_map.tile_center(0, 0), game_map, [], ResourceStorage())

    [npc_state] = serialize(game_map, npcs=[pawn], fauna=[])["npcs"]

    assert npc_state["isInWater"] is True


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
    fauna: list[Fauna] = [WildArcher(*game_map.tile_center(2, 1), game_map)]
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
    wild_archer = WildArcher(*game_map.tile_center(2, 1), game_map)
    wild_archer.link_battlefield(
        npcs=[pawn], arrows=arrows, clock=clock_at(WILD_ARCHER_GRACE_FRAMES)
    )
    sheep = Sheep(*game_map.tile_center(5, 3), game_map)
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
    sheep = Sheep(*game_map.tile_center(5, 3), game_map)
    state = serialize_state(
        game_map=game_map,
        resources=[Structure(1, 1, building_type="storage_hut")],
        npcs=[pawn],
        fauna=[sheep],
        arrows=[],
        storage=ResourceStorage(),
        log_messages=[],
        chat_messages=[],
        available_models=[],
        selected_model=SelectedModel(
            model=VOICE_MODEL, text=ScriptedOrderInterpreter(), voice=None
        ),
    )

    [hut], [pawn_state], [sheep_state] = state["resources"], state["npcs"], state["fauna"]
    assert (hut["footprint"], hut["height"]) == ({"width": 2, "depth": 2}, 1)
    assert hut["sprite"] == {"width": 2, "height": 3.0, "anchorX": 1.0, "anchorY": 3.0}
    assert pawn_state["sprite"] == {"width": 1.0, "height": 1.0, "anchorX": 0.5, "anchorY": 0.84375}
    assert sheep_state["footprint"] == {"width": 1, "depth": 1}


def test_the_map_carries_the_biome_of_each_tile(build_map: MapBuilder) -> None:
    game_map = build_map(["..", ".~"])
    game_map.biomes[1][1] = Biome.LAKE

    state = serialize(game_map, npcs=[], fauna=[])

    assert state["map"]["biomes"] == [["meadow", "meadow"], ["meadow", "lake"]]
