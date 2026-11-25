---
paths:
  - "game/**/*.py"
  - "api/**/*.py"
  - "server/**/*.py"
  - "*.py"
---

# Precise typing

`mypy --strict` runs on `game/`, `api/`, `server/` and `main.py`. Every new
function is fully annotated; a `# type: ignore` names its error code and is only
allowed on an untyped third-party API.

## Name discrete values with an enum

When a value ranges over a fixed set (an action, a state, a tile kind, a resource
kind), give it an enum, not a bare string. Follow the existing examples:
`game/npcs/actions.py` `State` / `ActionType`, `game/fauna/fauna.py` `FaunaState`,
`game/world/terrain.py` `TileType`, `game/world/npc_names.py` `NPCName`.

New string-valued sets use `enum.StrEnum`: members are `str`, so they serialize to
the same JSON the client already reads.

```python
# Don't
if action == "chop_wood":
    ...


# Do
class ResourceKind(StrEnum):
    WOOD = "wood"
    STONE = "stone"


if kind == ResourceKind.WOOD:
    ...
```

When an enum mirrors an external list (the actions the LLM may return in
`api/interpreter.py`, the actions the client sends), add a test that fails if the two
drift apart.

## Don't reach for `str` / `dict[str, Any]` when the shape is known

| Don't | Do |
|---|---|
| `kind: str` for a fixed set | a `StrEnum` |
| `dict[str, Any]` for a known record | a `TypedDict` or `@dataclass` |
| `-> dict` from a function you own | the concrete return type |
| `flag: bool` positional mode switch | keyword-only, or a 2-value enum |

`dict[str, Any]` stays acceptable for a JSON payload built for the client at the
entry point.

## Name the values you compare against

A threshold or a duration goes in `game/settings.py` (game tuning) or `constants.py`,
not inline: `if distance > ARCHER_RANGE`, not `if distance > 320`. A self-evident
`== 0` / `== 1` stays inline.
