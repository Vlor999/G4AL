---
paths:
  - "game/**/*.py"
  - "api/**/*.py"
  - "*.py"
  - "static/**/*.js"
---

# Identifier naming

## Spell words out

Local variables, parameters, fields, function names: write the word in full.

| Don't | Do |
|---|---|
| `res` | `resource` (or `response`, never the ambiguous one) |
| `st` | `storage` / `structure` / `state` |
| `idx` | `index` (`i` is fine for a loop counter) |
| `pos` | `position` |
| `tgt` | `target` |
| `msg` | `message` |
| `evt` | `event` |
| `cnt` | `count` |
| `dx`, `dy`, `col`, `row` | kept: established grid and vector conventions in this codebase |

## Function names start with a verb

`find_path`, `spawn_resources`, `enqueue_action`, `serialize_npcs`, `drawNpc`.
Not `path_for` or `npcs_json`.

## Boolean flags read as predicates

`is_walkable`, `has_target`, `should_flee`, `is_full`. Not `walkable: bool`.

## Match the domain vocabulary

The game already settled on `npc`, `pawn`, `archer`, `fauna`, `resource`, `structure`,
`storage`, `hut`, `tile`, `col`/`row`. Use those names, on the server and in
`static/`. Do not invent synonyms (`unit`, `villager`, `building`, `cell`) in new code.
