"""HUD panel, action buttons, and command input bar."""

from __future__ import annotations

from typing import List, Optional, Tuple, Callable, TYPE_CHECKING

import pygame

from game.settings import (
    UI_TOP_BAR_HEIGHT,
    UI_LEFT_PANEL_WIDTH,
    UI_RIGHT_PANEL_WIDTH,
    COLOR_UI_BG,
    COLOR_UI_TEXT,
    COLOR_UI_BUTTON,
    COLOR_UI_BUTTON_HOV,
    UI_FONT_SIZE,
    UI_FONT_SIZE_LARGE,
)
from game.npc import ActionType, Action
from game.sprites import get_sprite

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
        surface.blit(
            text,
            (
                self.rect.centerx - text.get_width() // 2,
                self.rect.centery - text.get_height() // 2,
            ),
        )

    def is_hovered(self, pos: Tuple[int, int]) -> bool:
        self.hovered = self.rect.collidepoint(pos)
        return self.hovered


# ─────────────────────────────────────────────────────────────────────────
#  HUD
# ─────────────────────────────────────────────────────────────────────────


class HUD:
    """UI overlay containing top resource bar, left action panel, and right log panel."""

    def __init__(self, screen_w: int, screen_h: int):
        self._screen_w = screen_w
        self._screen_h = screen_h
        self._font = None
        self._font_lg = None

        self.top_rect = pygame.Rect(0, 0, screen_w, UI_TOP_BAR_HEIGHT)
        self.left_rect = pygame.Rect(
            0, UI_TOP_BAR_HEIGHT, UI_LEFT_PANEL_WIDTH, screen_h - UI_TOP_BAR_HEIGHT
        )
        self.right_rect = pygame.Rect(
            screen_w - UI_RIGHT_PANEL_WIDTH,
            UI_TOP_BAR_HEIGHT,
            UI_RIGHT_PANEL_WIDTH,
            screen_h - UI_TOP_BAR_HEIGHT,
        )

        self._buttons: List[Button] = []
        self._build_buttons()

        # command input bar
        self._input_active = False
        self._input_text = ""
        self._input_rect = pygame.Rect(
            self.right_rect.x + 10,
            self.right_rect.bottom - 42,
            self.right_rect.width - 20,
            32,
        )
        self._on_command: Optional[Callable[[str], None]] = None

        # log / chat history
        self._log_messages: List[Tuple[str, int]] = []  # (text, spawn_frame)
        self._frame_count = 0

    def _wrap_text(
        self, text: str, font: pygame.font.Font, max_width: int
    ) -> List[str]:
        words = text.split(" ")
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.rstrip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.rstrip())
        return lines

    def resize(self, screen_w: int, screen_h: int):
        """Recalculate layout after the window is resized."""
        self._screen_w = screen_w
        self._screen_h = screen_h

        self.top_rect = pygame.Rect(0, 0, screen_w, UI_TOP_BAR_HEIGHT)
        self.left_rect = pygame.Rect(
            0, UI_TOP_BAR_HEIGHT, UI_LEFT_PANEL_WIDTH, screen_h - UI_TOP_BAR_HEIGHT
        )
        self.right_rect = pygame.Rect(
            screen_w - UI_RIGHT_PANEL_WIDTH,
            UI_TOP_BAR_HEIGHT,
            UI_RIGHT_PANEL_WIDTH,
            screen_h - UI_TOP_BAR_HEIGHT,
        )

        self._buttons.clear()
        self._build_buttons()
        self._input_rect = pygame.Rect(
            self.right_rect.x + 10,
            self.right_rect.bottom - 42,
            self.right_rect.width - 20,
            32,
        )

    def _ensure_fonts(self):
        if self._font is None:
            self._font = pygame.font.SysFont("consolas", UI_FONT_SIZE)
            self._font_lg = pygame.font.SysFont("consolas", UI_FONT_SIZE_LARGE)

    def _build_buttons(self):
        bx = self.left_rect.x + 20
        by = self.left_rect.y + 120
        bw, bh = self.left_rect.width - 40, 36
        gap = 10
        button_defs = [
            ("Chop Wood", ActionType.CHOP_WOOD),
            ("Mine Rock", ActionType.MINE_ROCK),
            ("Build", ActionType.BUILD),
            ("Plant", ActionType.PLANT_WHEAT),
            ("Eat", ActionType.EAT),
        ]
        for i, (label, at) in enumerate(button_defs):
            rect = pygame.Rect(bx, by + i * (bh + gap), bw, bh)
            self._buttons.append(Button(rect, label, at))

    # ── public ───────────────────────────────────────────────────────────

    def set_command_callback(self, callback: Callable[[str], None]):
        """Register a callback invoked when the player submits a text command."""
        self._on_command = callback

    def show_status(self, msg: str, duration_frames: int = 0):
        """Show a status message in the HUD log."""
        self._log_messages.append((msg, self._frame_count))
        # Keep only the last 15 messages so it doesn't grow forever
        if len(self._log_messages) > 15:
            self._log_messages.pop(0)

    def handle_click(
        self,
        pos: Tuple[int, int],
        selected_npcs: List["NPC"],
        build_col_row: Optional[Tuple[int, int]] = None,
    ) -> bool:
        """Returns True if click was consumed by the HUD."""
        # Is click inside any of the UI panels?
        in_ui = (
            self.top_rect.collidepoint(pos)
            or self.left_rect.collidepoint(pos)
            or self.right_rect.collidepoint(pos)
        )
        if not in_ui:
            self._input_active = False
            return False  # click is on the map

        # check input bar
        if self._input_rect.collidepoint(pos):
            self._input_active = True
            return True
        else:
            self._input_active = False

        # check left panel buttons
        if self.left_rect.collidepoint(pos):
            for btn in self._buttons:
                if btn.rect.collidepoint(pos):
                    self._dispatch(btn.action_type, selected_npcs, build_col_row)
                    return True

        return True  # consumed but no interactable hit

    def handle_keydown(self, event: pygame.event.Event) -> bool:
        """Process keyboard input for the text bar. Returns True if consumed."""
        if not self._input_active:
            return False
        if event.key == pygame.K_RETURN:
            cmd = self._input_text.strip()
            self._input_text = ""
            self._input_active = False
            if cmd and self._on_command:
                self._on_command(cmd)
            return True
        elif event.key == pygame.K_ESCAPE:
            self._input_active = False
            self._input_text = ""
            return True
        elif event.key == pygame.K_BACKSPACE:
            self._input_text = self._input_text[:-1]
            return True
        else:
            if event.unicode and event.unicode.isprintable():
                self._input_text += event.unicode
            return True

    def _dispatch(
        self,
        action_type: ActionType | str,
        npcs: List["NPC"],
        build_col_row: Optional[Tuple[int, int]],
    ):
        for npc in npcs:
            if action_type == ActionType.BUILD:
                target = build_col_row or npc.tile_pos
                npc.enqueue(Action(ActionType.BUILD, target=target))
            elif action_type == ActionType.PLANT_WHEAT:
                target = build_col_row or npc.tile_pos
                npc.enqueue(Action(ActionType.PLANT_WHEAT, target=target))
            else:
                npc.enqueue(Action(action_type))

    def update_hover(self, pos: Tuple[int, int]):
        for btn in self._buttons:
            btn.is_hovered(pos)

    # ── drawing ──────────────────────────────────────────────────────────

    def draw(
        self,
        surface: pygame.Surface,
        storage: "ResourceStorage",
        selected_npcs: List["NPC"],
        all_npcs: List["NPC"],
    ):
        self._frame_count += 1
        self._ensure_fonts()

        # Draw panel backgrounds
        pygame.draw.rect(surface, COLOR_UI_BG, self.top_rect)
        pygame.draw.rect(surface, (28, 40, 46), self.left_rect)
        pygame.draw.rect(surface, (28, 40, 46), self.right_rect)

        # Draw panel borders
        pygame.draw.line(
            surface,
            (100, 100, 100),
            self.top_rect.bottomleft,
            self.top_rect.bottomright,
            2,
        )
        pygame.draw.line(
            surface,
            (100, 100, 100),
            self.left_rect.topright,
            self.left_rect.bottomright,
            2,
        )
        pygame.draw.line(
            surface,
            (100, 100, 100),
            self.right_rect.topleft,
            self.right_rect.bottomleft,
            2,
        )

        # ── TOP BAR: resources ───────────────────────────────────────────
        rx = 20
        ry = self.top_rect.y + 10
        stock = storage.snapshot()
        res_data = [
            ("Wood:", stock.get("wood", 0), (139, 195, 74), "icon_wood.ppm"),
            ("Stone:", stock.get("stone", 0), (189, 189, 189), "icon_stone.ppm"),
            ("Gold:", stock.get("gold", 0), (255, 215, 0), "icon_gold.ppm"),
            ("Wheat:", stock.get("wheat", 0), (218, 195, 80), "icon_wheat.ppm"),
        ]
        for label, count, color, icon in res_data:
            # draw icon
            sprite = get_sprite(icon, (20, 20))
            surface.blit(sprite, (rx, ry))
            rx += 26
            # draw text
            rendered = self._font_lg.render(f"{label} {count}", True, color)
            surface.blit(rendered, (rx, ry - 2))
            rx += rendered.get_width() + 40

        # ── LEFT PANEL: Selection & Actions ──────────────────────────────
        lx = self.left_rect.x + 20
        ly = self.left_rect.y + 20

        sel_title = self._font_lg.render("Selection", True, COLOR_UI_TEXT)
        surface.blit(sel_title, (lx, ly))
        pygame.draw.line(
            surface, (80, 80, 80), (lx, ly + 25), (self.left_rect.right - 20, ly + 25)
        )
        ly += 35

        if selected_npcs:
            npc = selected_npcs[0]
            hunger_pct = int(npc.hunger / npc.max_hunger * 100)
            hunger_color = (255, 152, 0) if hunger_pct > 25 else (244, 67, 54)
            info_lines = [
                f"{npc.name}",
                f"HP: {npc.health}/{npc.max_health}",
                f"{npc.state.name}",
            ]
            for line in info_lines:
                rendered = self._font.render(line, True, COLOR_UI_TEXT)
                surface.blit(rendered, (lx, ly))
                ly += 22
            # hunger bar in the info area
            hunger_label = self._font.render(
                f"Hunger: {hunger_pct}%", True, hunger_color
            )
            surface.blit(hunger_label, (lx, ly))
            ly += 20
            bar_w, bar_h = 100, 10
            pygame.draw.rect(surface, (60, 60, 60), (lx, ly, bar_w, bar_h))
            fill_w = int(bar_w * npc.hunger / npc.max_hunger)
            if fill_w > 0:
                pygame.draw.rect(surface, hunger_color, (lx, ly, fill_w, bar_h))
        else:
            # Wrap standard hint text
            hint1 = self._font.render("Click an NPC to", True, (180, 180, 180))
            hint2 = self._font.render("give orders.", True, (180, 180, 180))
            surface.blit(hint1, (lx, ly))
            surface.blit(hint2, (lx, ly + 20))

        # action buttons
        for btn in self._buttons:
            btn.draw(surface, self._font)

        # ── RIGHT PANEL: Roster & Log ────────────────────────────────────
        tx = self.right_rect.x + 15
        ty = self.right_rect.y + 15

        # Roster
        title = self._font_lg.render("NPC Roster", True, COLOR_UI_TEXT)
        surface.blit(title, (tx, ty))
        pygame.draw.line(
            surface, (80, 80, 80), (tx, ty + 25), (self.right_rect.right - 15, ty + 25)
        )
        ty += 35
        for npc in all_npcs[:6]:  # Show max 6 NPCs
            sel_marker = "▸ " if npc.selected else "  "
            line = f"{sel_marker}{npc.name}  {npc.state.name}"
            color = (0, 230, 118) if npc.selected else (180, 180, 180)
            rendered = self._font.render(line, True, color)
            surface.blit(rendered, (tx, ty))
            ty += 20

        # Log
        ty += 15
        log_title = self._font_lg.render("Event Log", True, COLOR_UI_TEXT)
        surface.blit(log_title, (tx, ty))
        pygame.draw.line(
            surface, (80, 80, 80), (tx, ty + 25), (self.right_rect.right - 15, ty + 25)
        )
        ty += 35

        # Show messages that fit
        log_y = self._input_rect.top - 20
        max_w = self.right_rect.width - 30

        # Wrap messages and collect lines
        wrapped_lines = []
        for msg, _ in reversed(self._log_messages[-15:]):
            lines = self._wrap_text(msg, self._font, max_w)
            # Add reversed lines list so we draw bottom line first
            wrapped_lines.extend(reversed(lines))

        for line_str in wrapped_lines:
            label = self._font.render(line_str, True, (200, 200, 200))
            log_y -= 18
            surface.blit(label, (tx, log_y))
            if log_y < ty:  # ran out of space
                break

        # ── command input bar ────────────────────────────────────────────
        self._draw_input_bar(surface)

    def _draw_input_bar(self, surface: pygame.Surface):
        """Draw the text command input bar."""
        self._ensure_fonts()
        rect = self._input_rect
        # background
        border_color = (100, 255, 150) if self._input_active else (120, 120, 120)
        bg_color = (50, 60, 65) if self._input_active else (40, 48, 52)
        pygame.draw.rect(surface, bg_color, rect, border_radius=6)
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=6)

        # placeholder or text
        if self._input_text:
            display = self._input_text
        else:
            display = "Type a command... (e.g. 'Tomas go chop wood!')"
        color = COLOR_UI_TEXT if self._input_text else (130, 130, 130)
        text_surf = self._font.render(display, True, color)
        # clip to bar
        clip = pygame.Rect(0, 0, rect.width - 12, rect.height)
        surface.blit(text_surf, (rect.x + 6, rect.y + 7), area=clip)

        # blinking cursor
        if self._input_active and pygame.time.get_ticks() % 1000 < 500:
            cx = rect.x + 6 + min(text_surf.get_width(), rect.width - 14)
            pygame.draw.line(
                surface, COLOR_UI_TEXT, (cx, rect.y + 6), (cx, rect.bottom - 6), 2
            )

        # label
        label = self._font.render("Command:", True, (180, 180, 180))
        surface.blit(label, (rect.x - label.get_width() - 8, rect.y + 7))
