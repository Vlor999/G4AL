"""Arrows in flight: the record the client draws, and the arrow a shot releases."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, TypedDict

from game.constants import ARROW_IMPACT_HEIGHT, ARROW_LAUNCH_HEIGHT
from game.settings import ARCHER_ARROW_FLIGHT


class Team(StrEnum):
    BLUE = "blue"
    RED = "red"


class Arrow(TypedDict):
    fromX: float
    fromY: float
    toX: float
    toY: float
    frame: int
    totalFrames: int
    team: str


class Positioned(Protocol):
    @property
    def x(self) -> float: ...

    @property
    def y(self) -> float: ...


def build_arrow(*, shooter: Positioned, target: Positioned, team: Team) -> Arrow:
    """The arrow of a shot from *shooter* to *target*, on its first frame of flight."""
    return {
        "fromX": shooter.x,
        "fromY": shooter.y - ARROW_LAUNCH_HEIGHT,
        "toX": target.x,
        "toY": target.y - ARROW_IMPACT_HEIGHT,
        "frame": 0,
        "totalFrames": ARCHER_ARROW_FLIGHT,
        "team": team,
    }


def advance_arrows(arrows: list[Arrow]) -> None:
    """Move every arrow one frame on and drop the ones that landed, in place: archers
    and wild archers hold this same list."""
    for arrow in arrows:
        arrow["frame"] += 1
    arrows[:] = [arrow for arrow in arrows if arrow["frame"] < arrow["totalFrames"]]
