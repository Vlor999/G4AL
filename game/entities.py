"""Harvestable world entities: trees, rocks, and buildable structures."""

from __future__ import annotations

import random
from typing import List, Tuple, Optional, TYPE_CHECKING

import pygame

from game.settings import (
    TILE_SIZE,
    TREE_WOOD_YIELD,
    ROCK_STONE_YIELD,
    ROCK_GOLD_YIELD,
    WHEAT_YIELD,
    WHEAT_GROW_TIME,
)
from game.sprites import get_sprite

if TYPE_CHECKING:
    from game.map import GameMap


class Resource:
    """Base class for any harvestable map object sitting on a tile."""

    kind: str = "resource"

    def __init__(self, col: int, row: int, hp: int, yields: dict[str, int]):
        self.col = col
        self.row = row
        self.hp = hp
        self.max_hp = hp
        self.yields = yields  # {"wood": 10, …}
        self.depleted = False
        self.reserved_by: int | None = None  # NPC id that claimed this resource

    @property
    def world_pos(self) -> Tuple[float, float]:
        return (
            self.col * TILE_SIZE + TILE_SIZE // 2,
            self.row * TILE_SIZE + TILE_SIZE // 2,
        )

    def harvest_tick(self) -> Optional[dict[str, int]]:
        """Call once per action-frame. Returns yield dict when fully depleted."""
        if self.depleted:
            return None
        self.hp -= 1
        if self.hp <= 0:
            self.depleted = True
            return dict(self.yields)
        return None

    def draw(self, surface: pygame.Surface, camera: Tuple[int, int]):
        raise NotImplementedError


class Tree(Resource):
    kind = "tree"

    def __init__(self, col: int, row: int):
        super().__init__(
            col, row, hp=TREE_WOOD_YIELD * 3, yields={"wood": TREE_WOOD_YIELD}
        )
        # visual variation
        self._leaf_radius = random.randint(18, 26)
        self._trunk_w = random.randint(6, 10)
        self._trunk_h = random.randint(14, 20)

    def draw(self, surface: pygame.Surface, camera: Tuple[int, int]):
        if self.depleted:
            return
        cx, cy = self.world_pos
        sx, sy = cx - camera[0], cy - camera[1]
        sprite = get_sprite(
            "tree.ppm", (self._leaf_radius * 2, self._leaf_radius * 2 + 10)
        )
        surface.blit(
            sprite, (sx - sprite.get_width() // 2, sy - sprite.get_height() // 2 - 4)
        )
        # HP bar (small)
        if self.hp < self.max_hp:
            _draw_hp_bar(
                surface,
                sx,
                sy - sprite.get_height() // 2 - 10,
                self.hp,
                self.max_hp,
                30,
            )


class Rock(Resource):
    kind = "rock"

    def __init__(self, col: int, row: int, has_gold: bool = False):
        yields = {"stone": ROCK_STONE_YIELD}
        if has_gold:
            yields["gold"] = ROCK_GOLD_YIELD
        super().__init__(col, row, hp=ROCK_STONE_YIELD * 4, yields=yields)
        self.has_gold = has_gold
        self._w = random.randint(28, 38)
        self._h = random.randint(20, 28)

    def draw(self, surface: pygame.Surface, camera: Tuple[int, int]):
        if self.depleted:
            return
        cx, cy = self.world_pos
        sx, sy = cx - camera[0], cy - camera[1]
        sprite_name = "gold_rock.ppm" if self.has_gold else "rock.ppm"
        sprite = get_sprite(sprite_name, (self._w, self._h + 8))
        surface.blit(
            sprite, (sx - sprite.get_width() // 2, sy - sprite.get_height() // 2)
        )
        # HP bar
        if self.hp < self.max_hp:
            _draw_hp_bar(
                surface, sx, sy - sprite.get_height() // 2 - 6, self.hp, self.max_hp, 30
            )


class Structure(Resource):
    """A player-built structure (e.g. storage hut). Placeholder for v1."""

    kind = "structure"

    def __init__(self, col: int, row: int, build_progress: int = 0):
        super().__init__(col, row, hp=100, yields={})
        self.build_progress = build_progress  # 0..100
        self.built = False
        self._size = 40

    def build_tick(self):
        self.build_progress = min(100, self.build_progress + 1)
        if self.build_progress >= 100:
            self.built = True

    def draw(self, surface: pygame.Surface, camera: Tuple[int, int]):
        cx, cy = self.world_pos
        sx, sy = cx - camera[0], cy - camera[1]
        half = self._size // 2
        if self.built:
            sprite = get_sprite("structure.ppm", (self._size, self._size))
        else:
            sprite = get_sprite("construction.ppm", (self._size, self._size))
        surface.blit(sprite, (sx - half, sy - half))
        # progress bar while building
        if not self.built:
            _draw_hp_bar(surface, sx, sy - half - 10, self.build_progress, 100, 36)


class WheatField(Resource):
    """A plantable wheat field that grows over time and can be harvested."""

    kind = "wheat"

    def __init__(self, col: int, row: int):
        # hp here is the harvest effort (how many harvest_tick calls to collect).
        # Growth is tracked separately by self.growth.
        super().__init__(col, row, hp=10, yields={"wheat": WHEAT_YIELD})
        self.growth = 0  # 0..WHEAT_GROW_TIME
        self.fully_grown = False
        self.planted = True

    @property
    def growth_ratio(self) -> float:
        return min(1.0, self.growth / WHEAT_GROW_TIME)

    def grow_tick(self):
        """Call every frame. The field grows passively."""
        if self.depleted or self.fully_grown:
            return
        self.growth += 1
        if self.growth >= WHEAT_GROW_TIME:
            self.fully_grown = True

    def harvest_tick(self) -> Optional[dict[str, int]]:
        """Can only harvest when fully grown."""
        if not self.fully_grown or self.depleted:
            return None
        self.hp -= 1
        if self.hp <= 0:
            self.depleted = True
            return dict(self.yields)
        return None

    def draw(self, surface: pygame.Surface, camera: Tuple[int, int]):
        if self.depleted:
            return
        cx, cy = self.world_pos
        sx, sy = cx - camera[0], cy - camera[1]
        size = TILE_SIZE - 8
        half = size // 2

        if self.fully_grown:
            sprite = get_sprite("wheat_grown.ppm", (size, size))
        else:
            sprite = get_sprite("wheat_young.ppm", (size, size))
        surface.blit(sprite, (sx - half, sy - half))

        # growth bar
        if not self.fully_grown:
            _draw_hp_bar(surface, sx, sy - half - 4, self.growth, WHEAT_GROW_TIME, 30)
        elif self.fully_grown and not self.depleted:
            # "ready" indicator
            font = pygame.font.SysFont(None, 14)
            ready = font.render("READY", True, (255, 230, 80))
            surface.blit(ready, (sx - ready.get_width() // 2, sy - half - 10))


# ── helpers ──────────────────────────────────────────────────────────────


def _draw_hp_bar(surface, cx, top_y, current, maximum, width=30, height=5):
    ratio = max(0, current / maximum)
    bg = pygame.Rect(cx - width // 2, top_y, width, height)
    fg = pygame.Rect(cx - width // 2, top_y, int(width * ratio), height)
    pygame.draw.rect(surface, (60, 60, 60), bg)
    bar_color = (76, 175, 80) if ratio > 0.4 else (244, 67, 54)
    pygame.draw.rect(surface, bar_color, fg)


def spawn_resources(
    game_map: "GameMap", tree_count: int = 40, rock_count: int = 15
) -> List[Resource]:
    """Place trees and rocks randomly on walkable grass tiles."""
    resources: List[Resource] = []
    occupied: set[Tuple[int, int]] = set()

    def _random_walkable():
        for _ in range(200):
            c = random.randint(1, game_map.cols - 2)
            r = random.randint(1, game_map.rows - 2)
            if game_map.is_walkable(c, r) and (c, r) not in occupied:
                return c, r
        return None

    for _ in range(tree_count):
        pos = _random_walkable()
        if pos:
            occupied.add(pos)
            resources.append(Tree(*pos))

    for i in range(rock_count):
        pos = _random_walkable()
        if pos:
            occupied.add(pos)
            has_gold = i < rock_count // 3
            resources.append(Rock(*pos, has_gold=has_gold))

    return resources
