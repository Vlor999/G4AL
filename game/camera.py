"""Camera that scrolls with keyboard / mouse-edge and follows the map bounds."""

from __future__ import annotations

from typing import Tuple

import pygame

from game.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, CAMERA_SPEED, CAMERA_EDGE_MARGIN,
    MAP_WIDTH, MAP_HEIGHT, UI_PANEL_HEIGHT,
)


class Camera:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    @property
    def offset(self) -> Tuple[int, int]:
        return (int(self.x), int(self.y))

    def update(self, keys_pressed, mouse_pos: Tuple[int, int]):
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
        max_x = max(0, MAP_WIDTH - SCREEN_WIDTH)
        max_y = max(0, MAP_HEIGHT - (SCREEN_HEIGHT - UI_PANEL_HEIGHT))
        self.x = max(0.0, min(self.x, max_x))
        self.y = max(0.0, min(self.y, max_y))

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        return sx + self.x, sy + self.y
