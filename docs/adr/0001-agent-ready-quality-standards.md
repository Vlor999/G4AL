# 0001. Agent-ready quality standards

## Context

G4AL was built during a hackathon: no tests, no CI, no lint gate, no instructions
for coding agents. Agents and humans had to guess conventions.

## Decision

- Tooling installed through a uv dev group and configured in `ruff.toml`, `mypy.ini`
  (`--strict`) and `pyproject.toml`: ruff, mypy, pytest
  with coverage, vulture. `make check` runs all of them; CI runs the same targets.
- Pre-commit hooks: ruff, mypy, vulture, gitleaks.
- CI: quality job, gitleaks and `pip-audit`, CodeQL (Python and JavaScript). Actions
  and pre-commit hooks are pinned by commit SHA; Dependabot keeps them and the uv
  dependencies up to date.
- Agent context: `AGENTS.md` (read by every agent, imported by `CLAUDE.md`), rules in
  `.claude/rules/`, skills in `.agents/skills/` linked from `.claude/skills/`, a
  PostToolUse hook that runs ruff and mypy on each edited Python file, the `openwiki`
  MCP server in `.mcp.json`.
  Superseded on that point by [ADR 0005](0005-claude-md-as-agent-entry-point.md).
- The frontend has no lint toolchain: it stays plain ES modules without Node.
- Readiness is measured with `npx @kodus/agent-readiness . --no-web`.

## Consequences

Every PR passes `make check`. The existing code was brought to zero ruff and mypy
errors in the same change, so the gates block from the first PR.
