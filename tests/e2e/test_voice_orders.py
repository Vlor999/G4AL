"""Drive the voice order hand-off of GameEngine: interpreter answer in, NPC actions, log and voice lines out."""

from game.actions import ActionType
from game.orders import NpcOrder
from game.ports import OrderInterpretationError
from server.engine import GameEngine
from tests.fakes import RecordingSpeaker, ScriptedOrderInterpreter

_AUDIO = b"RIFF"


def test_an_empty_answer_is_logged_as_not_understood() -> None:
    engine = GameEngine(interpreter=ScriptedOrderInterpreter(), speaker=RecordingSpeaker())

    engine.interpret_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages[-1] == "No actions understood."


def test_a_failed_interpretation_leaves_the_game_unchanged() -> None:
    interpreter = ScriptedOrderInterpreter(error=OrderInterpretationError("network down"))
    engine = GameEngine(interpreter=interpreter, speaker=RecordingSpeaker())

    engine.interpret_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages == []


def test_orders_are_logged_and_only_accepted_lines_are_spoken() -> None:
    speaker = RecordingSpeaker()
    interpreter = ScriptedOrderInterpreter()
    engine = GameEngine(interpreter=interpreter, speaker=speaker)
    pawn = next(npc for npc in engine.npcs if npc.kind == "pawn")
    interpreter.orders = [
        NpcOrder(npc_id=pawn.id, npc_name=pawn.name, action_type=None, voice_line="Huh?"),
        NpcOrder(
            npc_id=pawn.id, npc_name=pawn.name, action_type=ActionType.EAT, voice_line="Food!"
        ),
    ]

    engine.interpret_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages[-2:] == [f'{pawn.name}: "Huh?"', f'{pawn.name}: "Food!"']
    assert speaker.lines == [("Food!", pawn.name)]
