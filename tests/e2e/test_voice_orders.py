"""Drive the voice order hand-off of GameEngine: interpreter answer in, NPC actions, log and voice lines out."""

from typing import Any

from flask.testing import FlaskClient

import server
from api.interpreter import CommandResponse, NPCOrder


class RecordingSpeaker:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str]] = []

    def speak(self, text: str, npc_name: str = "") -> None:
        self.lines.append((text, npc_name))


def read_log(client: FlaskClient) -> list[str]:
    state: dict[str, Any] = client.get("/api/state").get_json()
    log: list[str] = state["log"]
    return log


def test_an_empty_answer_is_logged_as_not_understood(client: FlaskClient) -> None:
    server.engine._pending_response = CommandResponse(n=0, actions=[])

    server.engine.tick()

    assert read_log(client)[-1] == "No actions understood."


def test_orders_are_logged_and_only_accepted_lines_are_spoken(client: FlaskClient) -> None:
    speaker = RecordingSpeaker()
    server.engine.tts = speaker  # type: ignore[assignment]
    pawn = next(npc for npc in server.engine.npcs if npc.kind == "pawn")
    server.engine._pending_response = CommandResponse(
        n=2,
        actions=[
            NPCOrder(npc_name=pawn.name, npc_id=pawn.id, action="dance", voice_line="Huh?"),
            NPCOrder(npc_name=pawn.name, npc_id=pawn.id, action="eat", voice_line="Food!"),
        ],
    )

    server.engine.tick()

    assert read_log(client)[-2:] == [f'{pawn.name}: "Huh?"', f'{pawn.name}: "Food!"']
    assert speaker.lines == [("Food!", pawn.name)]
