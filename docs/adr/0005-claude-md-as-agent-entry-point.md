# 0005. CLAUDE.md as the agent entry point

## Context

[ADR 0001](0001-agent-ready-quality-standards.md) made `AGENTS.md` the entry point
every agent reads, and `CLAUDE.md` held a single line importing it. The OpenWiki tool
also writes a managed block into `AGENTS.md` and rewrites it on each refresh, so the
file mixed hand-written instructions with generated text.

## Decision

- `CLAUDE.md` holds the agent instructions: layout, commands, rules, skills, the new
  Dev workflow section and the gotchas.
- `AGENTS.md` is a pointer to `CLAUDE.md`, followed by the OpenWiki block, which the
  tool keeps rewriting there.

## Consequences

- An agent other than Claude Code reads `AGENTS.md`, finds the pointer and must open
  `CLAUDE.md` to get the instructions.
- The agent-readiness score of ADR 0001 may change, because the checker may look for
  the instructions in `AGENTS.md`.
- OpenWiki keeps writing its block in `AGENTS.md`, so a refresh never touches
  `CLAUDE.md`.
