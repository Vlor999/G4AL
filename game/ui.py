"""HUD panel and action buttons for commanding selected NPCs."""

from __future__ import annotations

from typing import List, Optional, Tuple, TYPE_CHECKING

import pygame

from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, UI_PANEL_HEIGHT,
    COLOR_UI_BG, COLOR_UI_TEXT, COLOR_UI_BUTTON, COLOR_UI_BUTTON_HOV,
    UI_FONT_SIZE, UI_FONT_SIZE_LARGE,
)
from game.npc import ActionType, Action

if TYPE_CHECKING:
    from game.npc import NPC
    from game.storage import ResourceStorage


# ─────────────────────────────────────────────────────────────────────────
#  Button helper
# ─────────────────────────────────────────────────────────────────────────

class Button:
    def __init__(self, rect: pygame.Rect, label: str, action_type: ActionType | str):
        self.rect = rect
        self.label = label
        self.action_type = action_type
        self.hovered = False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        color = COLOR_UI_BUTTON_HOV if self.hovered else COLOR_UI_BUTTON
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, (200, 200, 200), self.rect, 1, border_radius=6)
        text = font.render(self.label, True, COLOR_UI_TEXT)
        surface.blit(text, (self.rect.centerx - text.get_width() // 2,
                            self.rect.centery - text.get_height() // 2))

    def is_hovered(self, pos: Tuple[int, int]) -> bool:
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered


# ─────────────────────────────────────────────────────────────────────────
#  HUD
# ─────────────────────────────────────────────────────────────────────────

class HUD:
    """Bottom panel showing resources, selected NPC info, and action buttons."""

    PANEL_Y = SCREEN_HEIGHT - UI_PANEL_HEIGHT

    def __init__(self):
        self._font = None
        self._font_lg = None
        self._buttons: List[Button] = []
        self._build_buttons()

    def _ensure_fonts(self):
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", UI_FONT_SIZE)
            self._font_lg = pygame.font.SysFont("consolas", UI_FONT_SIZE_LARGE)

    def _build_buttons(self):
        bx = 420
        by = self.PANEL_Y + 40
        bw, bh = 130, 36
        gap = 10
        button_defs = [
            ("⛏  Chop Wood", ActionType.CHOP_WOOD),
            ("⛏  Mine Rock", ActionType.MINE_ROCK),
            ("🏗  Build", ActionType.BUILD),
        ]
        for i, (label, at) in enumerate(button_defs):
            rect = pygame.Rect(bx + i * (bw + gap), by, bw, bh)
            self._buttons.append(Button(rect, label, at))

    # ── public ───────────────────────────────────────────────────────────

    def handle_click(self, pos: Tuple[int, int], selected_npcs: List["NPC"],
                     build_col_row: Optional[Tuple[int, int]] = None) -> bool:
        """Returns True if click was consumed by the HUD."""
        if pos[1] < self.PANEL_Y:
            return False  # click is on the map, not the panel
        for btn in self._buttons:
            if btn.rect.collidepoint(pos):
                self._dispatch(btn.action_type, selected_npcs, build_col_row)
                return True
        return True  # consumed but no button hit

    def _dispatch(self, action_type: ActionType | str, npcs: List["NPC"],
                  build_col_row: Optional[Tuple[int, int]]):
        for npc in npcs:
            if action_type == ActionType.BUILD:
                # build at NPC's current tile by default
                target = build_col_row or npc.tile_pos
                npc.enqueue(Action(ActionType.BUILD, target=target))
            else:
                npc.enqueue(Action(action_type))

    def update_hover(self, pos: Tuple[int, int]):
        for btn in self._buttons:
            btn.is_hovered(pos)

    # ── drawing ──────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, storage: "ResourceStorage",
             selected_npcs: List["NPC"], all_npcs: List["NPC"]):
        self._ensure_fonts()

        # panel background
        panel_rect = pygame.Rect(0, self.PANEL_Y, SCREEN_WIDTH, UI_PANEL_HEIGHT)
        pygame.draw.rect(surface, COLOR_UI_BG, panel_rect)
        pygame.draw.line(surface, (100, 100, 100), (0, self.PANEL_Y), (SCREEN_WIDTH, self.PANEL_Y), 2)

        # ── resources ────────────────────────────────────────────────────
        rx = 20
        ry = self.PANEL_Y + 12
        stock = storage.snapshot()
        res_labels = [
            (f"🪵 Wood: {stock.get('wood', 0)}", (139, 195, 74)),
            (f"🪨 Stone: {stock.get('stone', 0)}", (189, 189, 189)),
            (f"💰 Gold: {stock.get('gold', 0)}", (255, 215, 0)),
        ]
        for text, color in res_labels:
            rendered = self._font_lg.render(text, True, color)
            surface.blit(rendered, (rx, ry))
            rx += rendered.get_width() + 30

        # ── selected NPC info ────────────────────────────────────────────
        if selected_npcs:
            npc = selected_npcs[0]
            info_lines = [
                f"{npc.name} (#{npc.id})  HP: {npc.health}/{npc.max_health}",
                f"State: {npc.state.name}   Queue: {npc.queue_size}",
            ]
            iy = self.PANEL_Y + 50
            for line in info_lines:
                rendered = self._font.render(line, True, COLOR_UI_TEXT)
                surface.blit(rendered, (20, iy))
                iy += 22
        else:
            hint = self._font.render("Click an NPC to select it, then give orders.", True, (180, 180, 180))
            surface.blit(hint, (20, self.PANEL_Y + 55))

        # ── action buttons ───────────────────────────────────────────────
        for btn in self._buttons:
            btn.draw(surface, self._font)

        # ── NPC roster (right side) ──────────────────────────────────────
        rx = SCREEN_WIDTH - 220
        ry = self.PANEL_Y + 12
        title = self._font_lg.render("NPCs", True, COLOR_UI_TEXT)
        surface.blit(title, (rx, ry))
        ry += 28
        for npc in all_npcs[:6]:
            sel_marker = "▸ " if npc.selected else "  "
            line = f"{sel_marker}{npc.name}  {npc.state.name}"
            color = (0, 230, 118) if npc.selected else (180, 180, 180)
            rendered = self._font.render(line, True, color)
            surface.blit(rendered, (rx, ry))
            ry += 20
