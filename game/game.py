"""Main game loop – ties everything together."""

from __future__ import annotations

import sys
import threading
from typing import List

import pygame

from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
)
from game.map import GameMap
from game.entities import Resource, spawn_resources
from game.storage import ResourceStorage
from game.npc import NPC, Action, ActionType
from game.camera import Camera
from game.ui import HUD
from api.voice import VoiceRecorder
from api.logger import pipeline_logger

# Lazy-import the API so the game still runs without a key
try:
    from api.interpreter import (
        interpret_command, interpret_audio_command,
        register_npcs, NPCOrder,
    )
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        # core objects
        self.game_map = GameMap(seed=42)
        self.storage = ResourceStorage()
        self.resources: List[Resource] = spawn_resources(self.game_map)
        self.npcs: List[NPC] = []
        self.camera = Camera()
        self.hud = HUD()
        self.voice = VoiceRecorder(on_audio=self._on_voice_audio)
        self._voice_text: str | None = None  # set from bg thread, consumed in _update

        # spawn a few starting bots on walkable tiles near the centre
        self._spawn_initial_npcs(3)

        self.running = True
        self._selected: List[NPC] = []

        # register LLM integration
        self._sync_npc_roster()
        self.hud.set_command_callback(self._on_player_command)
        self._pending_response: CommandResponse | None = None   # filled by LLM thread

    # ── bootstrap ────────────────────────────────────────────────────────

    def _spawn_initial_npcs(self, count: int):
        cx, cy = self.game_map.cols // 2, self.game_map.rows // 2
        placed = 0
        for dc in range(-3, 4):
            for dr in range(-3, 4):
                c, r = cx + dc, cy + dr
                if self.game_map.is_walkable(c, r):
                    wx, wy = self.game_map.tile_center(c, r)
                    npc = NPC(wx, wy, self.game_map, self.resources, self.storage)
                    self.npcs.append(npc)
                    placed += 1
                    if placed >= count:
                        return

    def _sync_npc_roster(self):
        """Push current NPC list to the LLM interpreter."""
        if not _HAS_LLM:
            return
        register_npcs([{"id": n.id, "name": n.name} for n in self.npcs])

    # ── voice → Voxtral multimodal bridge ───────────────────────────────────────

    def _on_voice_audio(self, wav_bytes: bytes):
        """Called from voice bg thread with recorded WAV bytes.
        Sends audio directly to Voxtral for a single-call interpretation."""
        if not _HAS_LLM:
            return
        print(f"[voice] sending {len(wav_bytes)} bytes to Voxtral…")
        # Run the single multimodal API call in this bg thread
        order = interpret_audio_command(wav_bytes)
        if order:
            self._pending_order = order  # picked up in _update()

    # ── LLM command handling ─────────────────────────────────────────────

    _ACTION_MAP = {
        "chop_wood": ActionType.CHOP_WOOD,
        "mine_rock": ActionType.MINE_ROCK,
        "build": ActionType.BUILD,
        "move_to": ActionType.MOVE_TO,
    }

    def _on_player_command(self, text: str):
        """Called from the HUD when the player submits a text command."""
        if not _HAS_LLM:
            self.hud.show_status("LLM not available (missing mistralai or API key)")
            return
        self.hud.show_status("Thinking...")
        # run LLM call in a background thread to avoid freezing the game
        threading.Thread(target=self._llm_worker, args=(text,), daemon=True).start()

    def _llm_worker(self, text: str):
        response = interpret_command(text)
        self._pending_response = response  # picked up in _update()

    def _apply_pending_response(self):
        response = self._pending_response
        if response is None:
            return
        self._pending_response = None

        if not response.actions:
            self.hud.show_status("No actions understood.")
            return

        # log pipeline summary
        pipeline_logger.pipeline_summary(
            voice_text=self._voice_text or "",
            order=response.model_dump(),
        )

        status_parts: list[str] = []

        for order in response.actions:
            # find the matching NPC
            npc = None
            for n in self.npcs:
                if n.id == order.npc_id:
                    npc = n
                    break
            if npc is None and self.npcs:
                npc = self.npcs[0]
            if npc is None:
                continue

            # map the action
            action_type = self._ACTION_MAP.get(order.action.value if hasattr(order.action, 'value') else order.action)
            if action_type:
                if action_type == ActionType.BUILD:
                    npc.enqueue(Action(action_type, target=npc.tile_pos))
                else:
                    npc.enqueue(Action(action_type))

            # show the voice line as a speech bubble
            npc.say(order.voice_line, duration_frames=360)
            status_parts.append(f"{order.npc_name}: \"{order.voice_line}\"")

        # show combined status
        combined = "  |  ".join(status_parts) if status_parts else "Orders dispatched."
        self.hud.show_status(combined, duration_frames=360)

    # ── main loop ────────────────────────────────────────────────────────

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(FPS)
        pygame.quit()
        pipeline_logger.close()
        sys.exit()

    # ── events ───────────────────────────────────────────────────────────

    def _handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        self.hud.update_hover(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                # let HUD text input consume key first
                if self.hud.handle_keydown(event):
                    continue
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_g:
                    self.voice.start()

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_g:
                    self.voice.stop()
                    self.hud.show_status("Transcribing…", duration_frames=300)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_left_click(event.pos)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                self._on_right_click(event.pos)

    def _on_left_click(self, pos):
        # HUD consumes click?
        if self.hud.handle_click(pos, self._selected):
            return

        # try selecting an NPC
        wx, wy = self.camera.screen_to_world(pos[0], pos[1])
        clicked_npc = None
        for npc in self.npcs:
            if npc.contains_point(wx, wy):
                clicked_npc = npc
                break

        # deselect all
        for npc in self.npcs:
            npc.selected = False
        self._selected.clear()

        if clicked_npc:
            clicked_npc.selected = True
            self._selected.append(clicked_npc)

    def _on_right_click(self, pos):
        """Right-click on the map → move selected NPCs there."""
        if pos[1] >= HUD.PANEL_Y:
            return
        if not self._selected:
            return
        wx, wy = self.camera.screen_to_world(pos[0], pos[1])
        col, row = self.game_map.world_to_tile(wx, wy)
        for npc in self._selected:
            npc.enqueue(Action(ActionType.MOVE_TO, target=(col, row)))

    # ── update ───────────────────────────────────────────────────────────

    def _update(self):
        keys = pygame.key.get_pressed()
        self.camera.update(keys)

        # feed text command from HUD to the LLM pipeline
        if self._voice_text is not None:
            text = self._voice_text
            self._voice_text = None
            self._on_player_command(text)

        # apply LLM / Voxtral result if ready
        if self._pending_order is not None:
            self._apply_pending_order()

        for npc in self.npcs:
            npc.update()

    # ── draw ─────────────────────────────────────────────────────────────

    def _draw(self):
        cam = self.camera.offset

        # map
        self.game_map.draw(self.screen, cam)

        # resources
        for r in self.resources:
            r.draw(self.screen, cam)

        # NPCs (sorted by y for naive depth)
        for npc in sorted(self.npcs, key=lambda n: n.y):
            npc.draw(self.screen, cam)

        # HUD on top
        self.hud.draw(self.screen, self.storage, self._selected, self.npcs)

        pygame.display.flip()
