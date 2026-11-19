"""JSON the browser client reads (`docs/api.md`), built from the game state."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from game.actions import State as NpcState
from game.arrows import Arrow
from game.dimensions import OBJECT_DIMENSIONS, ObjectDimensions, ObjectKind
from game.entities import Resource, Rock, Structure, WheatField
from game.fauna import Fauna
from game.map import GameMap
from game.npc import NPC
from game.settings import TILE_SIZE
from game.storage import ResourceStorage


def serialize_state(
    *,
    game_map: GameMap,
    resources: Sequence[Resource],
    npcs: Sequence[NPC],
    fauna: Sequence[Fauna],
    arrows: Sequence[Arrow],
    storage: ResourceStorage,
    log_messages: Sequence[str],
) -> dict[str, Any]:
    """Build the full state payload; the caller holds the engine lock."""
    return {
        "map": _serialize_map(game_map),
        "resources": [
            _serialize_resource(resource) for resource in resources if not resource.depleted
        ],
        "npcs": [_serialize_npc(npc) for npc in npcs],
        "fauna": [_serialize_creature(creature) for creature in fauna],
        "arrows": [_serialize_arrow(arrow) for arrow in arrows],
        "storage": storage.snapshot(),
        "storageFullAlert": any(npc.state == NpcState.WAITING_DEPOSIT for npc in npcs),
        "log": list(log_messages[-20:]),
    }


def _serialize_map(game_map: GameMap) -> dict[str, Any]:
    return {
        "cols": game_map.cols,
        "rows": game_map.rows,
        "tileSize": TILE_SIZE,
        "tiles": [
            [int(game_map.tiles[row][col]) for col in range(game_map.cols)]
            for row in range(game_map.rows)
        ],
    }


def _serialize_resource(resource: Resource) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": resource.kind,
        "col": resource.col,
        "row": resource.row,
        "hp": resource.hp,
        "maxHp": resource.max_hp,
        **_serialize_dimensions(resource.dimensions),
    }
    if isinstance(resource, Rock):
        payload["hasGold"] = resource.has_gold
    elif isinstance(resource, Structure):
        payload["built"] = resource.built
        payload["buildProgress"] = resource.build_progress
        payload["buildingType"] = resource.building_type
    elif isinstance(resource, WheatField):
        payload["fullyGrown"] = resource.fully_grown
        payload["growthRatio"] = round(resource.growth_ratio, 2)
    return payload


def _serialize_npc(npc: NPC) -> dict[str, Any]:
    return {
        "id": npc.id,
        "name": npc.name,
        "kind": npc.kind,
        "controllable": npc.controllable,
        "allowedActions": [action.value for action in npc.allowed_actions],
        "x": round(npc.x, 1),
        "y": round(npc.y, 1),
        "tileCol": npc.tile_pos[0],
        "tileRow": npc.tile_pos[1],
        "health": round(npc.health, 1),
        "maxHealth": npc.max_health,
        "hunger": round(npc.hunger, 1),
        "maxHunger": npc.max_hunger,
        "state": npc.state.name,
        "actionType": npc.current_action_type.value if npc.current_action_type else "",
        "selected": npc.selected,
        "speechText": npc.visible_speech_text,
        "isFiring": npc.is_firing,
        "isDefending": npc.is_defending,
        "queueSize": npc.queue_size,
        "isCarrying": npc.is_carrying,
        "carrying": dict(npc.carrying),
        **_serialize_dimensions(OBJECT_DIMENSIONS[ObjectKind(npc.kind)]),
    }


def _serialize_creature(creature: Fauna) -> dict[str, Any]:
    return {
        "id": creature.id,
        "name": creature.name,
        "kind": creature.kind,
        "controllable": False,
        "x": round(creature.x, 1),
        "y": round(creature.y, 1),
        "tileCol": creature.tile_pos[0],
        "tileRow": creature.tile_pos[1],
        "health": round(creature.health, 1),
        "maxHealth": creature.max_health,
        "state": creature.state.name,
        "isFiring": creature.is_firing,
        **_serialize_dimensions(OBJECT_DIMENSIONS[ObjectKind(creature.kind)]),
    }


def _serialize_dimensions(dimensions: ObjectDimensions) -> dict[str, Any]:
    sprite = dimensions.sprite
    return {
        "footprint": {"width": dimensions.footprint_width, "depth": dimensions.footprint_depth},
        "height": dimensions.height,
        "sprite": {
            "width": sprite.width,
            "height": sprite.height,
            "anchorX": sprite.anchor_x,
            "anchorY": sprite.anchor_y,
        },
    }


def _serialize_arrow(arrow: Arrow) -> dict[str, Any]:
    progress = arrow["frame"] / max(1, arrow["totalFrames"])
    return {
        "fromX": round(arrow["fromX"], 1),
        "fromY": round(arrow["fromY"], 1),
        "toX": round(arrow["toX"], 1),
        "toY": round(arrow["toY"], 1),
        "progress": round(progress, 3),
        "team": arrow.get("team", "blue"),
    }
