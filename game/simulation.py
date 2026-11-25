"""One frame of the world: NPCs and fauna act, wheat grows, arrows fly, the dead leave,
the clock ticks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.arrows import Arrow, advance_arrows
from game.clock import WorldClock
from game.entities import Resource, WheatField
from game.fauna import Fauna, remove_dead_fauna

if TYPE_CHECKING:
    from game.npc import NPC


def advance_world(
    *,
    npcs: list[NPC],
    fauna: list[Fauna],
    resources: list[Resource],
    arrows: list[Arrow],
    clock: WorldClock,
) -> None:
    """Advance the world by one frame, mutating every list and the clock in place: NPCs
    and creatures hold references to them. The clock advances last, so during the n-th
    frame it reads n - 1 elapsed frames."""
    for npc in npcs:
        npc.update()
    for creature in fauna:
        creature.update()
    _grow_wheat_fields(resources)
    advance_arrows(arrows)
    remove_dead_fauna(fauna)
    _remove_dead_npcs(npcs)
    clock.advance()


def _grow_wheat_fields(resources: list[Resource]) -> None:
    for resource in resources:
        if isinstance(resource, WheatField):
            resource.grow_tick()


def _remove_dead_npcs(npcs: list[NPC]) -> None:
    """Drop the dead NPCs; when the selected one died, the first survivor takes the selection."""
    dead_npcs = [npc for npc in npcs if npc.health <= 0]
    if not dead_npcs:
        return
    selected_died = any(npc.selected for npc in dead_npcs)
    npcs[:] = [npc for npc in npcs if npc.health > 0]
    if selected_died and npcs:
        npcs[0].selected = True
