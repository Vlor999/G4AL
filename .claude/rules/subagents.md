---
description: "Protocol for launching implementation sub-agents on tickets: worktree, branch, context, output requirements, PR, review."
---

# Implementation sub-agents (ticket → PR)

**One ticket = one sub-agent = one worktree = one PR.**

## Launch

- **Model**: set the `model` parameter on every launch.
  - Opus: implementation (code, tests, PR), design, security review, a bug whose cause
    is not found.
  - Sonnet: bounded, mechanical task (docs, rename, repetitive migration).
  - Haiku: read-only search and exploration.
  - Fable: reserved for extreme-level fixes and planning. Ask the user first.
- **Isolation**: one worktree per ticket from `origin/dev`, under `.claude/worktrees/`
  (`git worktree add .claude/worktrees/<slug> -b <branch> origin/dev`, or the
  `worktree` skill). Never two agents on the same files.
- **Context in the prompt**: the ticket, `CLAUDE.md`, the applicable
  `.claude/rules/` files, the known entry files. The agent guesses nothing.
- **Architecture**: the prompt tells the agent to follow `.claude/rules/architecture.md`
  (and to load `ub-mode` when installed), to write its plan before coding, and to run
  the self-check of § Design before code before the push.
- **Economy**: few turns. Plan in the reply, each file written whole once, tests run
  after writing, gates run once at the end, no file the ticket does not ask for.
- **Reviewers**: a sub-agent never adds or requests a reviewer on a PR.

## Output requirements

1. `make check` is green before the push.
2. PR: `gh pr create --base dev`, title = conventional commit, body
   "Intention / Choices and points of attention". The body never asks a question.
3. Decisions (a tuning value, a library, a deviation) go in `docs/` and in the PR body.
4. What is left after the PR goes back to the orchestrator in the final report.

## After review

- A sub-agent does not launch agents; the orchestrator launches the reviewers
  (`mr-review` skill in read-only mode) and consolidates their findings.
- Review comments go back to the original agent, which fixes, pushes on the same
  branch and replies to each comment.
- Run in parallel only disjoint tickets (different modules).
