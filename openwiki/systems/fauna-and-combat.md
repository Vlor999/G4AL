---
type: system
title: Fauna, wild archers and combat
description: How sheep, the cat and hostile wild archers behave, how wild archers wait out a grace period at the start of the game, how player archers shoot and defend, and how both sides share one arrow list.
tags: [fauna, combat, archer, wild-archer, domain]
sources:
  - id: openwiki-source-0d6e319e6afac58dc6a7e0a5
    resource: repo://game/combat/arrows.py
  - id: openwiki-source-df9d4931c454d01a1203d548
    resource: repo://game/fauna/cat.py
  - id: openwiki-source-72a55b5222417e6181ee13d0
    resource: repo://game/fauna/fauna.py
  - id: openwiki-source-c15db07da1040d931905f3e8
    resource: repo://game/fauna/sheep.py
  - id: openwiki-source-b1f707a2f046fe69cc5f8030
    resource: repo://game/fauna/wild_archer.py
  - id: openwiki-source-8203e4edf7c52fb4960dac18
    resource: repo://game/npcs/archer.py
  - id: openwiki-source-5712b0541b5af89e006f4ba3
    resource: repo://game/settings.py
  - id: openwiki-source-9a049830ee6d0ec18662aeea
    resource: repo://game/simulation.py
  - id: openwiki-source-56bbbe1245e7c4236d9f98cc
    resource: repo://game/spawning.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
verified:
  - by: openwiki/0.5.2
    at: 2026-11-28T12:48:19.642Z
---

# Fauna, wild archers and combat

Non-player creatures live in `game/fauna/`, the player's ranged unit in `game/npcs/archer.py`, and what both sides share in `game/combat/`. All are part of the pure [Domain model](domain-model.md) and are advanced by `advance_world`, described in [Game loop and state push](../workflows/game-loop-and-state-push.md).

## Fauna

`Fauna` (`game/fauna/fauna.py`) is the base of every autonomous creature. Its ids start at 10,001, so they never collide with NPC ids in the client state. It has a `FaunaState` of idle, wandering, grazing or shooting. Each frame `update()` runs one behaviour phase: idle for a random timer, then graze or wander with even odds; a wander walks a path to a random walkable tile within `wander_radius`; a graze lasts a random time. Timers and choices draw from the map's `rng`. Subclasses set their stats as class attributes.

| Creature | Kind | Stats and behaviour |
|---|---|---|
| `Sheep` | `sheep` | 20 HP, speed 0.8. Wanders and grazes. Spawns on free grass, in a meadow when one is free. |
| `Cat` | `cat` | 50 HP, speed 0. `update()` does nothing; the client animates it. Spawns in the first free map corner. |
| `WildArcher` | `wild_archer` | 50 HP, speed 1.5, wander radius 8. Hostile, red team: patrols, chases and shoots. |

## Wild archers

`WildArcher` (`game/fauna/wild_archer.py`) replaces the base loop with idle, wandering and shooting phases.

- **Grace period.** While the world clock reads fewer than `WILD_ARCHER_GRACE_FRAMES` (7,200 frames, two minutes) elapsed frames, the target search finds no one, so wild archers only patrol. The clock comes from `link_battlefield` at spawn.
- **Target.** After that, the target is the nearest living NPC by tile distance (`find_nearest_living`), pawns and archers alike.
- **Idle.** When its idle timer ends, the wild archer shoots a target within `WILD_ARCHER_RANGE`, or chases one within `WILD_ARCHER_CHASE_RANGE` (6 tiles) by walking to the nearest walkable tile in range of it. Otherwise it patrols (35% chance) or idles again for 90 to 300 frames.
- **Wandering.** While walking, it scans every frame and starts shooting as soon as a target is in range.
- **Shot.** A shot cycle lasts `WILD_ARCHER_SHOOT_TIME` frames. At `ARCHER_FIRE_ANIM_TIME` frames before its end, the fire phase starts. If the target left range, the wild archer goes idle. Otherwise it deals `WILD_ARCHER_DAMAGE` and adds a red arrow. The cycle repeats while the target lives; a dead target sends it back to idle.

## Player archers

`Archer` extends `NPC` with kind `archer`, 70 HP and 1.1 times the pawn speed. Its allowed actions are move, shoot, defend and eat.

- **Shoot.** Finds the nearest living `wild_archer` in the shared fauna list and says "No enemies!" if none. Out of `ARCHER_RANGE`, it walks to the walkable tile in range nearest to itself, or says "Can't reach enemy!" when there is none. In range, it shoots. The cycle lasts `ARCHER_SHOOT_TIME` frames (96). Damage (`ARCHER_ARROW_DAMAGE`) and the blue arrow come when the fire phase starts, `ARCHER_FIRE_ANIM_TIME` (24) frames before the end, so at frame 72. At the end of a cycle it shoots again if the enemy is still in range, or follows it.
- **Target down.** When the target dies the archer says "Target down!", then scans again if defending, or ends the order.
- **Defend.** Sets a defending flag, says "Defending!" and scans within `ARCHER_DEFEND_SCAN_RADIUS` (6) tiles. While idle with an empty queue, a defending archer scans again every frame.
- **Cancel.** Any new `enqueue` clears defend mode, the target and the firing flag before the base `enqueue` runs.

## Combat helpers (`game/combat/`)

- `targeting.py`: `tile_distance` (Manhattan), `find_nearest_living` (the earliest candidate on a tie, optional maximum distance) and `find_walkable_tile_in_range` (reachability is not checked). Both sides use them.
- `arrows.py`: `Arrow` is a `TypedDict` the serializer reads by key, which is why `vulture_allowlist.py` lists its keys. `build_arrow` starts an arrow at the shooter's bow height and aims at the target's body, with `ARCHER_ARROW_FLIGHT` frames of flight and a `Team` (blue or red). `advance_arrows` moves each arrow one frame and drops the landed ones.

## Shared lists

Archers receive the world's `fauna` and `arrows` lists, and wild archers the `npcs` and `arrows` lists and the `WorldClock`, through `link_battlefield` at spawn (`game/spawning.py`). `advance_world` mutates every list in place: `advance_arrows`, `remove_dead_fauna` and the dead-NPC removal all assign to a slice. So the links stay valid and archers always see the current creatures. See [Testing and quality gates](../testing/quality-gates-and-tests.md) for the allowlist.

## Related pages

- [Pathfinding](pathfinding.md)
- [HTTP and Socket.IO contract](http-and-socketio-contract.md) for the `fauna` and `arrows` payloads
