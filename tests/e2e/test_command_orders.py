"""Drive the order hand-off of GameEngine: a typed or spoken command in, NPC actions,
game log, chat and voice lines out."""

import threading
from collections.abc import Callable

import pytest

from api.model_catalog import CatalogModel
from game.actions import ActionType
from game.orders import CommandRefused, NpcOrder, RefusalReason
from game.ports import OrderInterpretationError
from server.constants import CHAT_HISTORY_LENGTH
from server.engine import GameEngine
from tests.fakes import (
    TEXT_MODEL,
    VOICE_MODEL,
    RecordingSpeaker,
    ScriptedOrderInterpreter,
    build_model_selection,
    run_now,
)

_AUDIO = b"RIFF"
_TYPED = "Bob, chop wood"
_STARTED = "Interpreting the command..."

SendCommand = Callable[[GameEngine], object]


def send_typed(engine: GameEngine) -> object:
    engine.send_text_command(_TYPED)
    return None


def send_spoken(engine: GameEngine) -> object:
    return engine.send_audio_command(_AUDIO)


both_inputs = pytest.mark.parametrize(
    "send_command", [send_typed, send_spoken], ids=["typed", "spoken"]
)


def build_engine(
    interpreter: ScriptedOrderInterpreter, speaker: RecordingSpeaker | None = None
) -> GameEngine:
    return GameEngine(
        model_selection=build_model_selection(interpreter),
        speaker=speaker or RecordingSpeaker(),
        run_in_background=run_now,
    )


def order_for(npc_id: int, npc_name: str, action_type: ActionType, voice_line: str) -> NpcOrder:
    return NpcOrder(
        npc_id=npc_id, npc_name=npc_name, action_type=action_type, voice_line=voice_line
    )


@pytest.mark.parametrize(
    ("send_command", "received"),
    [(send_typed, _TYPED), (send_spoken, _AUDIO)],
    ids=["typed", "spoken"],
)
def test_the_command_reaches_the_interpreter_of_its_input(
    send_command: SendCommand, received: str | bytes
) -> None:
    interpreter = ScriptedOrderInterpreter()

    send_command(build_engine(interpreter))

    assert interpreter.commands == [received]


@both_inputs
def test_an_empty_answer_is_logged_as_not_understood(send_command: SendCommand) -> None:
    engine = build_engine(ScriptedOrderInterpreter())

    send_command(engine)
    engine.tick()

    assert engine.log_messages == [_STARTED, "No actions understood."]


@both_inputs
def test_a_failed_interpretation_tells_the_player_without_the_service_error(
    send_command: SendCommand,
) -> None:
    speaker = RecordingSpeaker()
    interpreter = ScriptedOrderInterpreter(error=OrderInterpretationError("network down"))
    engine = build_engine(interpreter, speaker)
    queues_before = [list(npc.action_queue) for npc in engine.npcs]

    send_command(engine)
    engine.tick()

    assert engine.log_messages == [_STARTED, "Command failed, try again."]
    assert [list(npc.action_queue) for npc in engine.npcs] == queues_before
    assert speaker.lines == []


def test_a_refused_answer_is_shown_in_the_game_log_and_nothing_is_spoken() -> None:
    speaker = RecordingSpeaker()
    refusal = CommandRefused(RefusalReason.UNKNOWN_ACTION)
    engine = build_engine(ScriptedOrderInterpreter(refusal=refusal), speaker)

    engine.send_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages[-1] == "Order refused: unknown action"
    assert speaker.lines == []


def test_orders_are_logged_and_only_accepted_lines_are_spoken() -> None:
    speaker = RecordingSpeaker()
    interpreter = ScriptedOrderInterpreter()
    engine = build_engine(interpreter, speaker)
    pawn = next(npc for npc in engine.npcs if npc.kind == "pawn")
    interpreter.orders = [
        order_for(pawn.id, pawn.name, ActionType.SHOOT, "Huh?"),
        order_for(pawn.id, pawn.name, ActionType.EAT, "Food!"),
    ]

    engine.send_audio_command(_AUDIO)
    engine.tick()

    assert engine.log_messages[-2:] == [f'{pawn.name}: "Huh?"', f'{pawn.name}: "Food!"']
    assert speaker.lines == [("Food!", pawn.name)]


@pytest.mark.parametrize(
    ("send_command", "command_message"),
    [
        (send_typed, {"kind": "typed_command", "text": _TYPED}),
        (send_spoken, {"kind": "spoken_command"}),
    ],
    ids=["typed", "spoken"],
)
def test_the_chat_shows_the_command_then_every_voice_line_of_its_answer(
    send_command: SendCommand, command_message: dict[str, str]
) -> None:
    interpreter = ScriptedOrderInterpreter()
    engine = build_engine(interpreter)
    pawn = next(npc for npc in engine.npcs if npc.kind == "pawn")
    interpreter.orders = [
        order_for(pawn.id, pawn.name, ActionType.SHOOT, "Huh?"),
        order_for(pawn.id, pawn.name, ActionType.CHOP_WOOD, "On it."),
    ]

    send_command(engine)
    engine.tick()

    assert engine.get_state()["chat"] == [
        command_message,
        {"kind": "voice_line", "npcName": pawn.name, "text": "Huh?"},
        {"kind": "voice_line", "npcName": pawn.name, "text": "On it."},
    ]


def test_answers_that_arrive_before_a_tick_all_apply_in_arrival_order() -> None:
    speaker = RecordingSpeaker()
    interpreter = ScriptedOrderInterpreter()
    engine = build_engine(interpreter, speaker)
    pawn = next(npc for npc in engine.npcs if npc.kind == "pawn")
    for voice_line, action_type in [
        ("Wood!", ActionType.CHOP_WOOD),
        ("Rock!", ActionType.MINE_ROCK),
    ]:
        interpreter.orders = [order_for(pawn.id, pawn.name, action_type, voice_line)]
        engine.send_text_command(_TYPED)

    engine.tick()

    assert engine.log_messages[-2:] == [f'{pawn.name}: "Wood!"', f'{pawn.name}: "Rock!"']
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
    engine = build_engine(interpreter, speaker)
    npc = next(npc for npc in engine.npcs if npc.kind == kind)
    interpreter.orders = [order_for(npc.id, npc.name, action_type, "Aye!")]

    engine.send_text_command(_TYPED)
    engine.tick()

    [npc_state] = [state for state in engine.get_state()["npcs"] if state["id"] == npc.id]
    assert npc_state["speechText"] == "Aye!"
    assert npc_state["actionType"] == action_type.value
    assert speaker.lines == [("Aye!", npc.name)]


@pytest.mark.parametrize(
    ("selected", "has_voice_adapter"),
    [(TEXT_MODEL, True), (VOICE_MODEL, False)],
    ids=["text-model", "provider-without-voice-adapter"],
)
def test_without_voice_input_a_spoken_command_is_refused_and_typing_still_works(
    selected: CatalogModel, has_voice_adapter: bool
) -> None:
    interpreter = ScriptedOrderInterpreter()
    model_selection = build_model_selection(
        interpreter, selected=selected, has_voice_adapter=has_voice_adapter
    )
    engine = GameEngine(
        model_selection=model_selection, speaker=RecordingSpeaker(), run_in_background=run_now
    )

    assert engine.send_audio_command(_AUDIO) is False
    engine.send_text_command(_TYPED)

    assert interpreter.commands == [_TYPED]
    assert engine.get_state()["hasVoiceInput"] is False
    assert engine.get_state()["chat"] == [{"kind": "typed_command", "text": _TYPED}]


def test_the_chat_keeps_only_the_latest_messages() -> None:
    engine = build_engine(ScriptedOrderInterpreter())

    for i in range(100):
        engine.send_text_command(f"order {i}")

    chat = engine.get_state()["chat"]
    assert len(chat) == CHAT_HISTORY_LENGTH
    assert chat[-1] == {"kind": "typed_command", "text": "order 99"}


@both_inputs
def test_sending_a_command_logs_once_the_game_loop_lock_is_free(
    send_command: SendCommand,
) -> None:
    engine = build_engine(ScriptedOrderInterpreter())

    with engine._lock:
        sender = threading.Thread(target=send_command, args=(engine,))
        sender.start()
        sender.join(timeout=0.1)
        assert engine.log_messages == []
    sender.join()

    assert engine.log_messages[0] == _STARTED


def test_a_model_switch_applies_from_the_next_command_and_not_to_one_already_sent() -> None:
    interpreter = ScriptedOrderInterpreter()
    pending_work: list[Callable[[], None]] = []
    engine = GameEngine(
        model_selection=build_model_selection(interpreter, selected=VOICE_MODEL),
        speaker=RecordingSpeaker(),
        run_in_background=pending_work.append,
    )

    engine.send_text_command("sent before the switch")
    assert engine.select_model(TEXT_MODEL.model_id) is True
    engine.send_text_command("sent after the switch")
    for work in pending_work:
        work()

    assert interpreter.model_ids == [VOICE_MODEL.model_id, TEXT_MODEL.model_id]
    state = engine.get_state()
    assert (state["selectedModelId"], state["hasVoiceInput"]) == (TEXT_MODEL.model_id, False)


def test_a_model_outside_the_available_ones_is_not_selected() -> None:
    interpreter = ScriptedOrderInterpreter()
    engine = GameEngine(
        model_selection=build_model_selection(interpreter, available_models=[VOICE_MODEL]),
        speaker=RecordingSpeaker(),
        run_in_background=run_now,
    )

    assert engine.select_model(TEXT_MODEL.model_id) is False
    assert engine.select_model("gpt-unknown") is False
    engine.send_text_command(_TYPED)

    assert interpreter.model_ids == [VOICE_MODEL.model_id]
