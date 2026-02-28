"""Main game loop – ties everything together."""

from __future__ import annotations

import sys
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

        # spawn a few starting bots on walkable tiles near the centre
        self._spawn_initial_npcs(3)

        self.running = True
        self._selected: List[NPC] = []

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

    # ── main loop ────────────────────────────────────────────────────────

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()

    # ── events ───────────────────────────────────────────────────────────

    def _handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        self.hud.update_hover(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

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
        mouse = pygame.mouse.get_pos()
        self.camera.update(keys, mouse)

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
