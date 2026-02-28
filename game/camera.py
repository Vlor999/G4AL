"""Camera that scrolls with keyboard / mouse-edge and follows the map bounds."""

from __future__ import annotations

from typing import Tuple

import pygame

from game.settings import (
    CAMERA_SPEED,
    MAP_WIDTH,
    MAP_HEIGHT,
    UI_TOP_BAR_HEIGHT,
    UI_LEFT_PANEL_WIDTH,
    UI_RIGHT_PANEL_WIDTH,
)


class Camera:
    def __init__(self, screen_w: int, screen_h: int):
        self.x = 0.0
        self.y = 0.0
        self._screen_w = screen_w
        self._screen_h = screen_h

    def resize(self, screen_w: int, screen_h: int):
        """Called when the window is resized."""
        self._screen_w = screen_w
        self._screen_h = screen_h

    @property
    def offset(self) -> Tuple[int, int]:
        return (int(self.x), int(self.y))

    def update(self, keys_pressed):
        dx = dy = 0.0

        # keyboard
        if keys_pressed[pygame.K_LEFT] or keys_pressed[pygame.K_a]:
            dx -= CAMERA_SPEED
        if keys_pressed[pygame.K_RIGHT] or keys_pressed[pygame.K_d]:
            dx += CAMERA_SPEED
        if keys_pressed[pygame.K_UP] or keys_pressed[pygame.K_w]:
            dy -= CAMERA_SPEED
        if keys_pressed[pygame.K_DOWN] or keys_pressed[pygame.K_s]:
            dy += CAMERA_SPEED
        self.x += dx
        self.y += dy

        # clamp
        view_w = self._screen_w - UI_LEFT_PANEL_WIDTH - UI_RIGHT_PANEL_WIDTH
        view_h = self._screen_h - UI_TOP_BAR_HEIGHT

        max_x = max(0, MAP_WIDTH - view_w)
        max_y = max(0, MAP_HEIGHT - view_h)
        self.x = max(0.0, min(self.x, max_x))
        self.y = max(0.0, min(self.y, max_y))

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        # sx, sy are relative to the playable view area (offset by UI panels)
        return sx + self.x - UI_LEFT_PANEL_WIDTH, sy + self.y - UI_TOP_BAR_HEIGHT
