# 0004. Game sub-packages with downward imports

## Context

`game/` held 29 modules side by side. NPC types, fauna, the world, resources, combat
and orders sat in one flat folder, and nothing stopped a low-level module from
importing a high-level one.

## Decision

- `game/` is split into sub-packages, each with an empty `__init__.py` and no
  re-export:

  | Layer, top to bottom | Modules |
  |---|---|
  | top | `spawning.py`, `simulation.py`, `ports.py` |
  | `orders/` | `orders.py`, `direct_orders.py`, `chat.py` |
  | `npcs/` and `fauna/` | `actions.py`, `npc_base.py`, `npc.py`, `archer.py`; `fauna.py`, `sheep.py`, `cat.py`, `wild_archer.py`, `fauna_spawning.py` |
  | `combat/` | `arrows.py`, `targeting.py` |
  | `resources/` | `entities.py`, `storage.py` |
  | `world/` | `map.py`, `map_generation.py`, `terrain.py`, `pathfinding.py`, `dimensions.py`, `npc_names.py`, `clock.py` |

  `settings.py` and `constants.py` stay at the root, outside the layers, because every
  package reads them.
- A `layers` contract in `pyproject.toml` lets a package import only the ones below
  it, `TYPE_CHECKING` imports included. `npcs` and `fauna` share a layer: the archer
  and the wild archer name each other's types.
- `chat.py` (the player's commands and the NPCs' voice lines) goes to `orders/`: it
  holds what the player orders and what the NPCs answer, and imports nothing from
  `game`.
- `clock.py` (`WorldClock`) goes to `world/`, the bottom layer: the wild archer in
  `fauna/` reads it, and it imports nothing.
- `tests/` stays flat.

The duplicates the quality gate reported on the moved files were removed on the way:

- `Fauna._enter_timed_state` starts idling, grazing and the wild archer's shot, with
  one `_state_duration` for the current state.
- `Cat`, `Sheep` and `WildArcher` set their health and speed as class attributes, and
  `Cat` and `Sheep` their name too, so their constructors no longer repeat the base
  one. `WildArcher` still picks its name from the map's name pool.
- `NPCBase._start_performing` starts every timed piece of work of the pawn and the
  archer's shot. The archer and the wild archer keep their own state machines, since
  `npcs` and `fauna` do not share a base class.
- `world.pathfinding.find_nearest_tile` holds the breadth-first search that planting
  and building copied.

## Consequences

- A module that needs a type from a higher layer fails `lint-imports`: the type
  moves down, or the dependency goes through a port or an injected value.
- Imports name the sub-package: `from game.world.map import GameMap`.
