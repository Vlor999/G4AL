---
paths:
  - "game/**/*.py"
  - "api/**/*.py"
  - "*.py"
  - "static/**/*.js"
---

# File organization

## One concern per file

A file answers "what does this own?" in one sentence. If the sentence has an "and",
it needs two files.

Concerns that always live in their own module:

- **External I/O clients**: Mistral, ElevenLabs, the audio mixer, the log files. Each
  gets one module under `api/` that owns credentials, the client object and every
  call. Other code calls that module, never the SDK.
- **Pure types**: domain dataclasses and enums in a module without the logic that
  uses them, so an adapter can import them without importing the game loop.
- **Serialization for the client**: one place builds the JSON the client reads.

## Length budget

Aim for files under ~500 lines. Past that, point at a clear reason (an exhaustive test
suite, a data table). `game/npc.py` (~1100 lines) and `static/renderer.js` (~950
lines) are over budget: a PR that adds to them extracts first (for example
pathfinding out of `npc.py`, one draw module per entity kind out of `renderer.js`).

## Strategy split for alternative behaviours

When a type or a flag selects between two implementations of a step (pawn vs archer
actions, sheep vs wild archer behaviour), each branch is its own named method or
subclass, and the shared part stays in one place. The dispatcher reads as a thin
switch.

## Re-exports when splitting

When you split a module, re-export the moved public symbols from the old location in
the same PR, and drop the re-exports once the callers moved:

```python
from game.pathfinding import find_path  # noqa: F401
```
