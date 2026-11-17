---
paths:
  - "game/**/*.py"
  - "api/**/*.py"
  - "server/**/*.py"
  - "*.py"
  - "static/**/*.js"
  - "tests/**/*.py"
---

# Language

Under `tests/`, only the « Comments » section applies.

## Source code is English

All comments, docstrings, log messages, error strings and identifiers are in English.
New lines in a file that has French content are English; pre-existing French stays
until its file is refactored.

## Text a model reads

Prompt bodies and LLM instructions (`api/interpreter.py`, `api/roster.py`) are English.
The language the NPCs answer in is stated in the prompt itself, never assumed.

## French content keeps its diacritics

When a string is intentionally French (an NPC voice line example, a French doc), it
keeps every accent: `bâtiment`, `récolter`, `forêt`.

## Comments

A comment says what the code cannot say. There are two kinds, and nothing else is
worth writing.

- **Interface comment** (module, class, public function or method, port): write one
  when the signature and the names do not tell a caller everything they need: side
  effects, preconditions, what an empty or `None` return means, what is raised, the
  invariants a caller must keep. When the signature says it all, write nothing.
- **Why comment**, inside a body: a hidden constraint, a counterintuitive choice, or a
  trap someone already fell into (a frame-count unit, a thread-safety constraint
  around the game loop).

Never restate the code, describe a field its name already describes, or tell the
history of a change. Section banners (`# ═══ Data types ═══`) are not comments: a file
that needs them needs splitting (`file-organization.md`).

**Refactoring a file starts with a purge.** When a PR changes a file's structure
(splits, merges or moves code, reshapes a class), delete every comment and docstring
in it first, then write back only what the two kinds above call for. Never delete tool
directives (`# noqa`, `# type: ignore[...]`, `# pragma`, `# fmt:`, shebangs) or a
docstring read at run time.

## Temporary code gets a TODO

When you add code that must be deleted later (a compatibility shim, a debug hook),
mark it immediately:

```
# TODO: delete when <condition>. Deletion plan: <what to remove>.
```
