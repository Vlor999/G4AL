from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Any

from flask_socketio import SocketIO
from loguru import logger

from game.npcs.npc import NPC
from game.orders.chat import ChatMessage, NpcVoiceLine, PlayerCommand, SpokenCommand, TypedCommand
from game.orders.direct_orders import DirectOrder, DirectOrderOutcome, apply_direct_order
from game.orders.orders import CommandRefused, NpcOrder, apply_orders
from game.ports import OrderInterpretationError, VoiceLineSpeaker
from game.settings import FPS
from game.simulation import advance_world
from game.spawning import spawn_world
from game.world.map import GameMap
from server.constants import CHAT_HISTORY_LENGTH, MAP_SEED, STATE_PUSH_INTERVAL_FRAMES
from server.model_selection import ModelSelection
from server.serialization import serialize_state


@dataclass(frozen=True)
class _InterpretationFailed:
    """The interpreter service failed on a command; the player is told on the next tick."""


_InterpreterAnswer = list[NpcOrder] | CommandRefused
_CommandAnswer = _InterpreterAnswer | _InterpretationFailed


def _run_in_daemon_thread(work: Callable[[], None]) -> None:
    threading.Thread(target=work, daemon=True).start()


class GameEngine:
    """Game state and its 60 FPS loop; every public method is safe to call from any thread.

    Commands go to the interpreters of the model selected in ``model_selection`` when
    they are sent, and the replies of the NPCs through ``speaker``; the entry point
    builds them and owns their lifecycle. ``run_in_background`` runs each blocking
    interpreter call off the calling thread.
    """

    def __init__(
        self,
        *,
        model_selection: ModelSelection,
        speaker: VoiceLineSpeaker,
        run_in_background: Callable[[Callable[[], None]], None] = _run_in_daemon_thread,
    ) -> None:
        self.game_map = GameMap(seed=MAP_SEED)
        world = spawn_world(self.game_map)
        self.storage = world.storage
        self.resources = world.resources
        self.storage_hut = world.storage_hut
        self.npcs = world.npcs
        self.fauna = world.fauna
        self.arrows = world.arrows
        self.clock = world.clock
        self._model_selection = model_selection
        self._speaker = speaker
        self._run_in_background = run_in_background
        self.log_messages: list[str] = []
        self.chat_messages: deque[ChatMessage] = deque(maxlen=CHAT_HISTORY_LENGTH)
        self._lock = threading.Lock()
        self._running = False
        self._pending_answers: deque[_CommandAnswer] = deque()

    def _add_log(self, message: str) -> None:
        """Append to the game log, keeping the last 50 lines; the caller holds ``self._lock``."""
        self.log_messages.append(message)
        if len(self.log_messages) > 50:
            self.log_messages.pop(0)

    def tick(self) -> None:
        with self._lock:
            while self._pending_answers:
                self._apply_answer(self._pending_answers.popleft())
            advance_world(
                npcs=self.npcs,
                fauna=self.fauna,
                resources=self.resources,
                arrows=self.arrows,
                clock=self.clock,
            )

    def give_direct_order(self, order: DirectOrder) -> DirectOrderOutcome:
        with self._lock:
            return apply_direct_order(order, npcs=self.npcs, game_map=self.game_map)

    def select_npc(self, npc_id: int) -> bool:
        """Select this NPC alone; returns False, changing nothing, when no NPC has this id."""
        with self._lock:
            if self._find_npc(npc_id) is None:
                return False
            for npc in self.npcs:
                npc.selected = npc.id == npc_id
            return True

    def deselect_all(self) -> None:
        with self._lock:
            for npc in self.npcs:
                npc.selected = False

    def _apply_answer(self, answer: _CommandAnswer) -> None:
        if isinstance(answer, _InterpretationFailed):
            self._add_log("Command failed, try again.")
            return
        if isinstance(answer, CommandRefused):
            self._add_log(f"Order refused: {answer.reason}")
            return
        if not answer:
            self._add_log("No actions understood.")
            return

        for outcome in apply_orders(self.npcs, answer):
            order = outcome.order
            if outcome.is_spoken:
                self._speaker.speak(order.voice_line, order.npc_name)
            self._add_log(f'{order.npc_name}: "{order.voice_line}"')
            self.chat_messages.append(NpcVoiceLine(order.npc_name, order.voice_line))

    def discard_resources(self, amounts: Mapping[str, int]) -> dict[str, int]:
        """Discard from storage; returns what was actually removed per resource."""
        with self._lock:
            return self.storage.discard_resources(amounts)

    def release_npcs_waiting_deposit(self) -> int:
        """Make every NPC waiting for storage space drop its load; returns how many did."""
        with self._lock:
            return sum(npc.give_up_waiting_deposit() for npc in self.npcs)

    def _find_npc(self, npc_id: int) -> NPC | None:
        for npc in self.npcs:
            if npc.id == npc_id:
                return npc
        return None

    def get_state(self) -> dict[str, Any]:
        """Return the state payload the client reads (`docs/api.md`)."""
        with self._lock:
            return serialize_state(
                game_map=self.game_map,
                resources=self.resources,
                npcs=self.npcs,
                fauna=self.fauna,
                arrows=self.arrows,
                storage=self.storage,
                log_messages=self.log_messages,
                chat_messages=self.chat_messages,
                available_models=self._model_selection.available_models,
                selected_model=self._model_selection.selected(),
            )

    def select_model(self, model_id: str) -> bool:
        """Send the next commands to ``model_id``; a command already sent keeps its
        model. Returns False, changing nothing, when no available model has this id."""
        return self._model_selection.select(model_id)

    def send_text_command(self, command: str) -> None:
        """Interpret a typed command in the background with the selected model; its
        orders apply on a later tick."""
        selected = self._model_selection.selected()
        interpret = partial(selected.text.interpret_text, command, model_id=selected.model.model_id)
        self._start_interpretation(TypedCommand(command), interpret)

    def send_audio_command(self, wav_bytes: bytes) -> bool:
        """Interpret a voice command in the background with the selected model; its
        orders apply on a later tick.

        Returns False, doing nothing, when the selected model does not hear audio.
        """
        selected = self._model_selection.selected()
        if selected.voice is None:
            return False
        interpret = partial(
            selected.voice.interpret_voice, wav_bytes, model_id=selected.model.model_id
        )
        self._start_interpretation(SpokenCommand(), interpret)
        return True

    def _start_interpretation(
        self, command: PlayerCommand, interpret: Callable[[], _InterpreterAnswer]
    ) -> None:
        with self._lock:
            self._add_log("Interpreting the command...")
            self.chat_messages.append(command)
        self._run_in_background(partial(self._interpret_and_queue, interpret))

    def _interpret_and_queue(self, interpret: Callable[[], _InterpreterAnswer]) -> None:
        # A failed service call is logged on the server; the game log only says the
        # command failed, without the service's error text.
        answer: _CommandAnswer
        try:
            answer = interpret()
        except OrderInterpretationError as error:
            logger.bind(event="order_interpretation").warning(f"Command dropped: {error}")
            answer = _InterpretationFailed()
        with self._lock:
            self._pending_answers.append(answer)

    _frame_count: int = 0
    _state_push_interval: int = STATE_PUSH_INTERVAL_FRAMES

    def run_loop(self, socketio: SocketIO | None = None) -> None:
        """Run the game loop in the current thread until ``stop``, pushing the state to ``socketio``."""
        self._running = True
        self._frame_count = 0
        is_push_failing = False
        frame_duration = 1.0 / FPS
        while self._running:
            frame_start = time.perf_counter()
            self.tick()
            self._frame_count += 1

            if socketio and self._frame_count % self._state_push_interval == 0:
                try:
                    socketio.emit("state", self.get_state(), namespace="/")
                except Exception as exc:  # noqa: BLE001 - a failed push must not stop the game loop
                    # Logged once per failure streak: pushes run ~20 times a second.
                    if not is_push_failing:
                        logger.bind(event="state_push").warning(f"State push failed: {exc}")
                    is_push_failing = True
                else:
                    if is_push_failing:
                        logger.bind(event="state_push").info("State push recovered")
                    is_push_failing = False

            elapsed = time.perf_counter() - frame_start
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self) -> None:
        self._running = False
