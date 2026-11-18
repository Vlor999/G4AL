from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from typing import Any

from flask_socketio import SocketIO
from loguru import logger

from api.logger import pipeline_logger
from game.direct_orders import DirectOrder, DirectOrderOutcome, apply_direct_order
from game.entities import WheatField
from game.map import GameMap
from game.npc import NPC
from game.orders import CommandRefused, NpcOrder, apply_orders
from game.ports import OrderInterpretationError, OrderInterpreter, VoiceLineSpeaker
from game.settings import FPS
from game.spawning import spawn_world
from server.serialization import serialize_state


class GameEngine:
    """Game state and its 60 FPS loop; every public method is safe to call from any thread.

    Voice commands go through ``interpreter`` and the replies of the NPCs through
    ``speaker``; the entry point builds both and owns their lifecycle.
    """

    def __init__(self, *, interpreter: OrderInterpreter, speaker: VoiceLineSpeaker) -> None:
        self.game_map = GameMap(seed=42)
        world = spawn_world(self.game_map)
        self.storage = world.storage
        self.resources = world.resources
        self.storage_hut = world.storage_hut
        self.npcs = world.npcs
        self.fauna = world.fauna
        self.arrows = world.arrows
        self._interpreter = interpreter
        self._speaker = speaker
        self.log_messages: list[str] = []
        self._lock = threading.Lock()
        self._running = False
        self._pending_orders: list[NpcOrder] | CommandRefused | None = None

    def _add_log(self, msg: str) -> None:
        self.log_messages.append(msg)
        if len(self.log_messages) > 50:
            self.log_messages.pop(0)

    def tick(self) -> None:
        with self._lock:
            if self._pending_orders is not None:
                self._apply_pending_orders()

            for npc in self.npcs:
                npc.update()

            for creature in self.fauna:
                creature.update()

            for r in self.resources:
                if isinstance(r, WheatField):
                    r.grow_tick()

            # Mutated in place: archers and wild archers share this list.
            for arrow in self.arrows:
                arrow["frame"] += 1
            self.arrows[:] = [a for a in self.arrows if a["frame"] < a["totalFrames"]]

            self.fauna = [f for f in self.fauna if f.health > 0]

            # Mutated in place: the wild archers share this list.
            dead_npcs = [n for n in self.npcs if n.health <= 0]
            if dead_npcs:
                selected_died = any(n.selected for n in dead_npcs)
                self.npcs[:] = [n for n in self.npcs if n.health > 0]
                if selected_died and self.npcs:
                    self.npcs[0].selected = True

    def give_direct_order(self, order: DirectOrder) -> DirectOrderOutcome:
        with self._lock:
            return apply_direct_order(order, npcs=self.npcs, game_map=self.game_map)

    def select_npc(self, npc_id: int) -> bool:
        """Select this NPC alone; returns False, changing nothing, when no NPC has this id."""
        with self._lock:
            if self._find_npc(npc_id) is None:
                return False
            for n in self.npcs:
                n.selected = n.id == npc_id
            return True

    def deselect_all(self) -> None:
        with self._lock:
            for n in self.npcs:
                n.selected = False

    def _apply_pending_orders(self) -> None:
        orders = self._pending_orders
        self._pending_orders = None
        if isinstance(orders, CommandRefused):
            self._add_log(f"Order refused: {orders.reason}")
            return
        if not orders:
            self._add_log("No actions understood.")
            return

        for outcome in apply_orders(self.npcs, orders):
            order = outcome.order
            if outcome.is_spoken:
                self._speaker.speak(order.voice_line, order.npc_name)
            self._add_log(f'{order.npc_name}: "{order.voice_line}"')

    def discard_resources(self, amounts: Mapping[str, int]) -> dict[str, int]:
        """Discard from storage; returns what was actually removed per resource."""
        with self._lock:
            return self.storage.discard_resources(amounts)

    def release_npcs_waiting_deposit(self) -> int:
        """Make every NPC waiting for storage space drop its load; returns how many did."""
        with self._lock:
            return sum(npc.give_up_waiting_deposit() for npc in self.npcs)

    def _find_npc(self, npc_id: int) -> NPC | None:
        for n in self.npcs:
            if n.id == npc_id:
                return n
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
            )

    def send_audio_command(self, wav_bytes: bytes) -> None:
        """Interpret a voice command in a worker thread; its orders apply on a later tick."""
        self._add_log("Listening...")
        threading.Thread(
            target=self.interpret_audio_command, args=(wav_bytes,), daemon=True
        ).start()

    def interpret_audio_command(self, wav_bytes: bytes) -> None:
        """Interpret a voice command and queue its orders for the next tick.

        Blocks for the interpreter call: run it off the game loop thread. A refused
        answer reaches the game log on the next tick; a failed service call is logged
        and leaves the game unchanged.
        """
        try:
            orders = self._interpreter.interpret(wav_bytes)
        except OrderInterpretationError as error:
            logger.bind(event="order_interpretation").warning(f"Voice command dropped: {error}")
            return
        with self._lock:
            self._pending_orders = orders

    _frame_count: int = 0
    _ws_push_interval: int = 3  # frames: ~20 Hz at 60 FPS

    def run_loop(self, socketio_ref: SocketIO | None = None) -> None:
        """Run the game loop in the current thread until ``stop``, pushing the state to ``socketio_ref``."""
        self._running = True
        self._frame_count = 0
        is_push_failing = False
        target_dt = 1.0 / FPS
        while self._running:
            t0 = time.perf_counter()
            self.tick()
            self._frame_count += 1

            if socketio_ref and self._frame_count % self._ws_push_interval == 0:
                try:
                    socketio_ref.emit("state", self.get_state(), namespace="/")
                except Exception as exc:  # noqa: BLE001 - a failed push must not stop the game loop
                    # Logged once per failure streak: pushes run ~20 times a second.
                    if not is_push_failing:
                        logger.bind(event="state_push").warning(f"State push failed: {exc}")
                    is_push_failing = True
                else:
                    if is_push_failing:
                        logger.bind(event="state_push").info("State push recovered")
                    is_push_failing = False

            elapsed = time.perf_counter() - t0
            sleep_time = target_dt - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self) -> None:
        self._running = False
        pipeline_logger.close()
