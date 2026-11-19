---
paths:
  - "game/**/*.py"
  - "api/**/*.py"
  - "server/**/*.py"
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
suite, a data table). `static/renderer.js` (~950 lines) is over budget: a PR that adds
to it extracts first (for example one draw module per entity kind).

## Strategy split for alternative behaviours

When a type or a flag selects between two implementations of a step (pawn vs archer
actions, sheep vs wild archer behaviour), each branch is its own named method or
subclass, and the shared part stays in one place. The dispatcher reads as a thin
switch.

## No re-export when splitting

When you split a module, move the public symbols and update every caller (code,
tests, docs) in the same PR. Leave nothing behind in the old module: no re-export,
no alias, no `# noqa: F401` import. The old location then fails loudly instead of
hiding a second path to the same symbol.

A temporary re-export is acceptable only when a caller cannot move in the same PR,
for example code owned by another open PR. Mark it with the TODO from
`language.md` (condition and deletion plan), and name the PR that deletes it in the
description.
