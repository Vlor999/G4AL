---
type: system
title: Fauna, wild archers and combat
description: How sheep, the cat and hostile wild archers behave, how player archers shoot and defend, and how both sides share one arrow list.
tags: [fauna, combat, archer, wild-archer, domain]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:41:00.050Z
sources:
  - id: openwiki-source-4dfd58450f4ea0193b27ec59
    resource: repo://game/archer.py
  - id: openwiki-source-1118e86fbc148d23a1bc4bc9
    resource: repo://game/creatures.py
  - id: openwiki-source-5712b0541b5af89e006f4ba3
    resource: repo://game/settings.py
  - id: openwiki-source-56bbbe1245e7c4236d9f98cc
    resource: repo://game/spawning.py
  - id: openwiki-source-0d5ad3511dcf5d6f5ad53c00
    resource: repo://server/engine.py
generated: { by: "claude-code", at: "2026-11-18T09:41:00.050Z" }
---

# Fauna, wild archers and combat

Non-player creatures live in `game/creatures.py` and the player's ranged unit in `game/archer.py`. Both are part of the pure [Domain model](domain-model.md) and are advanced by the loop described in [Game loop and state push](../workflows/game-loop-and-state-push.md).

## Fauna

`Fauna` is the base of every autonomous creature. It has an id starting at 10,001, so ids do not collide with NPC ids, and a `FaunaState` of idle, wandering, grazing or shooting. Each frame `update()` runs one behaviour phase: idle for a timer then randomly graze or wander, wandering follows a path chosen near the current tile.

| Creature | Kind | Behaviour |
|---|---|---|
| `Sheep` | `sheep` | Slow (0.8), 20 HP. Wanders and grazes. |
| `Cat` | `cat` | Stationary, `update()` does nothing; the client animates it. |
| `WildArcher` | `wild_archer` | Hostile, 50 HP, speed 1.5. Patrols, chases and shoots. |

## Wild archers

`WildArcher` overrides the loop with a shoot state:

- When idle it looks for the nearest living NPC by tile distance. Within `WILD_ARCHER_RANGE` it starts shooting; within six tiles it chases; otherwise it idles or patrols a radius of eight tiles. While wandering it keeps scanning and starts shooting when a target is in range.
- A shot has an aim phase then a fire phase at the end of `WILD_ARCHER_SHOOT_TIME` frames. The damage (`WILD_ARCHER_DAMAGE`) is applied and a red arrow added at the fire transition, unless the target moved out of range. The cycle repeats while the target lives.

## Player archers

`Archer` extends `NPC` with kind `archer`, 70 HP and a slightly faster speed. Its allowed actions are move, shoot, defend and eat.

- **Shoot.** Finds the nearest living `wild_archer` in the shared fauna list, says "No enemies!" if none, walks to within `ARCHER_RANGE` and shoots. The shot cycle lasts `ARCHER_SHOOT_TIME` frames (96); damage and the blue arrow come when the fire phase starts, `ARCHER_FIRE_ANIM_TIME` (24) frames before the end, so at frame 72. It keeps shooting while the enemy lives and is in range.
- **Defend.** Sets a defending flag and scans within `ARCHER_DEFEND_SCAN_RADIUS` tiles. While idle with an empty queue, a defending archer scans again every frame.
- **Cancel.** Any new `enqueue` clears defend mode, the target and the firing flag before the base `enqueue` runs.

## Battlefield linking

Archers and wild archers receive the world's `fauna`, `npcs` and `arrows` lists by `link_battlefield`, by reference, at spawn (`game/spawning.py`). The engine mutates `npcs` and `arrows` in place (slice assignment), so those links stay valid. It does not do that for `fauna`: each tick it rebinds `self.fauna` to a new filtered list, so archers keep the list they were given at spawn and no longer see the engine's current fauna (tracked as #22). An `Arrow` is a `TypedDict` the serializer reads by key, which is why `vulture_allowlist.py` lists its keys. See [Testing and quality gates](../testing/quality-gates-and-tests.md).

## Related pages

- [Pathfinding](pathfinding.md)
- [HTTP and Socket.IO contract](http-and-socketio-contract.md) for the `fauna` and `arrows` payloads
