"""One frame of the world: NPCs and fauna act, wheat grows, arrows fly, the dead leave."""

from __future__ import annotations

from typing import TYPE_CHECKING

from game.arrows import Arrow, advance_arrows
from game.entities import Resource, WheatField
from game.fauna import Fauna, remove_dead_fauna

if TYPE_CHECKING:
    from game.npc import NPC


def advance_world(
    *, npcs: list[NPC], fauna: list[Fauna], resources: list[Resource], arrows: list[Arrow]
) -> None:
    """Advance the world by one frame, mutating every list in place: NPCs and creatures
    hold references to them."""
    for npc in npcs:
        npc.update()
    for creature in fauna:
        creature.update()
    _grow_wheat_fields(resources)
    advance_arrows(arrows)
    remove_dead_fauna(fauna)
    _remove_dead_npcs(npcs)


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
