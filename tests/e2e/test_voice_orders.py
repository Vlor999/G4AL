"""Drive the voice order hand-off of GameEngine: interpreter answer in, NPC actions, log and voice lines out."""

import pytest

from game.actions import ActionType
from game.orders import CommandRefused, NpcOrder, RefusalReason
from game.ports import OrderInterpretationError
from server.engine import GameEngine
from tests.fakes import RecordingSpeaker, ScriptedOrderInterpreter

_AUDIO = b"RIFF"


def test_an_empty_answer_is_logged_as_not_understood() -> None:
    engine = GameEngine(interpreter=ScriptedOrderInterpreter(), speaker=RecordingSpeaker())

    engine.interpret_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages[-1] == "No actions understood."


def test_a_failed_interpretation_tells_the_player_without_the_service_error() -> None:
    speaker = RecordingSpeaker()
    interpreter = ScriptedOrderInterpreter(error=OrderInterpretationError("network down"))
    engine = GameEngine(interpreter=interpreter, speaker=speaker)
    queues_before = [list(npc.action_queue) for npc in engine.npcs]

    engine.interpret_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages == ["Voice command failed, try again."]
    assert [list(npc.action_queue) for npc in engine.npcs] == queues_before
    assert speaker.lines == []


def test_a_refused_answer_is_shown_in_the_game_log_and_nothing_is_spoken() -> None:
    speaker = RecordingSpeaker()
    refusal = CommandRefused(RefusalReason.UNKNOWN_ACTION)
    engine = GameEngine(interpreter=ScriptedOrderInterpreter(refusal=refusal), speaker=speaker)

    engine.interpret_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages[-1] == "Order refused: unknown action"
    assert speaker.lines == []


def test_orders_are_logged_and_only_accepted_lines_are_spoken() -> None:
    speaker = RecordingSpeaker()
    interpreter = ScriptedOrderInterpreter()
    engine = GameEngine(interpreter=interpreter, speaker=speaker)
    pawn = next(npc for npc in engine.npcs if npc.kind == "pawn")
    interpreter.orders = [
        NpcOrder(
            npc_id=pawn.id, npc_name=pawn.name, action_type=ActionType.SHOOT, voice_line="Huh?"
        ),
        NpcOrder(
            npc_id=pawn.id, npc_name=pawn.name, action_type=ActionType.EAT, voice_line="Food!"
        ),
    ]

    engine.interpret_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages[-2:] == [f'{pawn.name}: "Huh?"', f'{pawn.name}: "Food!"']
    assert speaker.lines == [("Food!", pawn.name)]


def test_answers_that_arrive_before_a_tick_all_apply_in_arrival_order() -> None:
    speaker = RecordingSpeaker()
    interpreter = ScriptedOrderInterpreter()
    engine = GameEngine(interpreter=interpreter, speaker=speaker)
    pawn = next(npc for npc in engine.npcs if npc.kind == "pawn")
    for voice_line, action_type in [
        ("Wood!", ActionType.CHOP_WOOD),
        ("Rock!", ActionType.MINE_ROCK),
    ]:
        interpreter.orders = [
            NpcOrder(
                npc_id=pawn.id, npc_name=pawn.name, action_type=action_type, voice_line=voice_line
            )
        ]
        engine.interpret_audio_command(_AUDIO)

    engine.tick()

    assert engine.log_messages == [f'{pawn.name}: "Wood!"', f'{pawn.name}: "Rock!"']
    assert speaker.lines == [("Wood!", pawn.name), ("Rock!", pawn.name)]


@pytest.mark.parametrize(
    ("kind", "action_type"),
    [("pawn", ActionType.CHOP_WOOD), ("archer", ActionType.DEFEND)],
)
def test_an_accepted_order_shows_its_voice_line_in_a_bubble_and_speaks_it(
    kind: str, action_type: ActionType
) -> None:
    speaker = RecordingSpeaker()
    interpreter = ScriptedOrderInterpreter()
    engine = GameEngine(interpreter=interpreter, speaker=speaker)
    npc = next(npc for npc in engine.npcs if npc.kind == kind)
    interpreter.orders = [
        NpcOrder(npc_id=npc.id, npc_name=npc.name, action_type=action_type, voice_line="Aye!")
    ]

    engine.interpret_audio_command(_AUDIO)
    engine.tick()

    [npc_state] = [state for state in engine.get_state()["npcs"] if state["id"] == npc.id]
    assert npc_state["speechText"] == "Aye!"
    assert npc_state["actionType"] == action_type.value
    assert speaker.lines == [("Aye!", npc.name)]
