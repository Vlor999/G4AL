"""Load PPM sprites and convert them to pygame Surfaces with transparency."""

from __future__ import annotations

import os
from typing import Dict, Tuple

import pygame

_ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Magenta = transparent key
_TRANSPARENT = (255, 0, 255)

_cache: Dict[str, pygame.Surface] = {}


def _load_ppm(name: str) -> pygame.Surface:
    """Load a P3 PPM file and return a Surface with colorkey transparency."""
    path = os.path.join(_ASSET_DIR, name)
    with open(path, "r") as f:
        # skip comments
        line = f.readline().strip()
        assert line == "P3", f"Expected P3 header, got {line}"
        # read width/height/max_val (skip comments)
        tokens: list[str] = []
        while len(tokens) < 3:
            line = f.readline().strip()
            if line.startswith("#"):
                continue
            tokens.extend(line.split())
        w, h = int(tokens[0]), int(tokens[1])

        # read pixel data
        nums: list[int] = []
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            nums.extend(int(x) for x in line.split())

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    idx = 0
    for y in range(h):
        for x in range(w):
            r, g, b = nums[idx], nums[idx + 1], nums[idx + 2]
            idx += 3
            if (r, g, b) != _TRANSPARENT:
                surf.set_at((x, y), (r, g, b, 255))
    return surf


def get_sprite(name: str, scale: Tuple[int, int] | None = None) -> pygame.Surface:
    """Get a cached sprite by filename. Optionally scale to (w, h)."""
    key = f"{name}_{scale}" if scale else name
    if key not in _cache:
        base = _load_ppm(name)
        if scale:
            base = pygame.transform.scale(base, scale)
        _cache[key] = base
    return _cache[key]
