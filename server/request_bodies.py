"""Parses the JSON bodies of the HTTP routes into typed values (`docs/api.md`)."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import TypeGuard

from game.constants import STORED_RESOURCE_KINDS
from game.npcs.actions import ActionType
from game.orders.direct_orders import DirectOrder
from server.constants import MAX_COMMAND_CHARACTERS


class InvalidRequestError(ValueError):
    """A request body that breaks the contract; the message is safe to send to the client."""


def parse_action_order(body: object) -> DirectOrder:
    """Parse `{"npcId": int, "action": str, "target"?: [col, row]}`."""
    fields = _require_object(body)
    action = fields.get("action")
    try:
        action_type = ActionType(action)
    except ValueError:
        raise InvalidRequestError(f"unknown action: {action!r}") from None
    target = fields.get("target")
    return _build_order(
        npc_id=_require_int(fields, "npcId"),
        action_type=action_type,
        target=None if target is None else _parse_tile(target),
    )


def parse_move_order(body: object) -> DirectOrder:
    """Parse `{"npcId": int, "col": int, "row": int}` into a `move_to` order."""
    fields = _require_object(body)
    tile = (_require_int(fields, "col"), _require_int(fields, "row"))
    return _build_order(
        npc_id=_require_int(fields, "npcId"), action_type=ActionType.MOVE_TO, target=tile
    )


def parse_selected_npc_id(body: object) -> int | None:
    """Parse `{"npcId": int}`, or `{}` that selects no NPC (returns ``None``)."""
    fields = _require_object(body)
    if "npcId" not in fields:
        return None
    return _require_int(fields, "npcId")


def parse_discard_amounts(body: object) -> dict[str, int]:
    """Parse `{"<stored resource>": non-negative int, ...}`."""
    fields = _require_object(body)
    unknown = sorted(set(fields) - set(STORED_RESOURCE_KINDS))
    if unknown:
        raise InvalidRequestError(f"unknown resources: {', '.join(unknown)}")
    amounts = {resource: _require_int(fields, resource) for resource in fields}
    if any(amount < 0 for amount in amounts.values()):
        raise InvalidRequestError("discarded amounts must not be negative")
    return amounts


def parse_audio_base64(body: object) -> bytes:
    """Decode the audio of `{"audio_b64": str}`."""
    encoded = body.get("audio_b64") if isinstance(body, dict) else None
    if not isinstance(encoded, str):
        raise InvalidRequestError("multipart audio file or JSON audio_b64 string required")
    try:
        return base64.b64decode(encoded, validate=True)
    # ValueError, the parent of binascii.Error: a non-ASCII string fails before decoding.
    except ValueError:
        raise InvalidRequestError("audio_b64 is not valid base64") from None


def parse_command_text(body: object) -> str:
    """Parse `{"text": str}`: the typed command, stripped, neither empty nor longer
    than ``MAX_COMMAND_CHARACTERS``."""
    text = _require_object(body).get("text")
    if not isinstance(text, str):
        raise InvalidRequestError("text must be a string")
    command = text.strip()
    if not command:
        raise InvalidRequestError("text must not be empty")
    if len(command) > MAX_COMMAND_CHARACTERS:
        raise InvalidRequestError(f"text longer than {MAX_COMMAND_CHARACTERS} characters")
    return command


def parse_model_id(body: object) -> str:
    """Parse `{"modelId": str}`."""
    model_id = _require_object(body).get("modelId")
    if not isinstance(model_id, str):
        raise InvalidRequestError("modelId must be a string")
    return model_id


def _require_object(body: object) -> Mapping[str, object]:
    if not isinstance(body, dict):
        raise InvalidRequestError("body must be a JSON object")
    return body


def _require_int(fields: Mapping[str, object], name: str) -> int:
    value = fields.get(name)
    if not _is_integer(value):
        raise InvalidRequestError(f"{name} must be an integer")
    return value


def _is_integer(value: object) -> TypeGuard[int]:
    # bool is a subclass of int: true and false are not numbers in this contract.
    return isinstance(value, int) and not isinstance(value, bool)


def _parse_tile(value: object) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2 or not all(map(_is_integer, value)):
        raise InvalidRequestError("target must be [col, row], two integers")
    col, row = value
    return col, row


def _build_order(
    *, npc_id: int, action_type: ActionType, target: tuple[int, int] | None
) -> DirectOrder:
    try:
        return DirectOrder(npc_id=npc_id, action_type=action_type, target=target)
    except ValueError as error:
        raise InvalidRequestError(str(error)) from None
