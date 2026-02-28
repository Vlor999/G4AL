"""Harvestable world entities: trees, rocks, and buildable structures."""

from __future__ import annotations

import random
from typing import List, Tuple, Optional, TYPE_CHECKING

from game.settings import (
    TILE_SIZE,
    TREE_WOOD_YIELD,
    ROCK_STONE_YIELD,
    ROCK_GOLD_YIELD,
    WHEAT_YIELD,
    WHEAT_GROW_TIME,
)

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


class Tree(Resource):
    kind = "tree"

    def __init__(self, col: int, row: int):
        super().__init__(
            col, row, hp=TREE_WOOD_YIELD * 3, yields={"wood": TREE_WOOD_YIELD}
        )


class Rock(Resource):
    kind = "rock"

    def __init__(self, col: int, row: int, has_gold: bool = False):
        yields = {"stone": ROCK_STONE_YIELD}
        if has_gold:
            yields["gold"] = ROCK_GOLD_YIELD
        super().__init__(col, row, hp=ROCK_STONE_YIELD * 4, yields=yields)
        self.has_gold = has_gold


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
