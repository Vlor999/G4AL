---
name: mr-review
description: Review a GitHub pull request of G4AL against the project rules (AGENTS.md, .claude/rules/) and docs, and report findings ranked by severity. Use when the user explicitly requests a review of a pull request (by number or the current branch).
disable-model-invocation: false
---

# Pull Request Review

Reviews a GitHub pull request and produces findings prioritized by importance and relevance to the code changes.

**Pick the mode first.**
- **Read-only mode**: the review is delegated (a sub-agent reviewing for an orchestrator) or the user asks for read-only. Do Steps 1, 2 and 3 below, then return the review table in the final report. Do not write the review file, do not spawn sub-agents, do not commit, do not post on GitHub.
- **Full mode**: any other case. Do Steps 1 and 2 below, then follow [FULL-MODE.md](FULL-MODE.md) (multi-agent review, technical validation, review file).

---

## Step 1 — Preflight

- Identify the pull request: `gh pr view <number>` gives its source and target branches and its body; `gh pr diff <number>` gives the diff. Without a number, assume the source branch is the current branch and the target is `dev`, and confirm with the user (AskUserQuestion). Branches may live in a worktree under `.claude/worktrees/`.
- Run `git fetch` so the local repository is up to date with the remote branches.
- Check the working tree. If modified or staged files exist, determine whether they affect the PR review. If they do not, continue without modifying them. If they affect the reviewed changes or prevent a reliable comparison, ask the user to resolve the state before proceeding.

---

## Step 2 — Rule Gathering

- Read `AGENTS.md`, every file under `.claude/rules/`, `docs/architecture.md`, `docs/api.md` (client/server contract), `docs/adr/`, and any other documentation or configuration the change touches.
- Apply `.claude/rules/architecture.md` to any Python or JavaScript the PR adds or changes. Check each point below on the modules the PR adds or changes:
  - **Import direction.** List the imports of each module and compare them with the layer table. `game/` imports nothing from `api/`, `server.py`, Flask, Socket.IO, Mistral, ElevenLabs or pygame. An import under `TYPE_CHECKING` counts.
  - **Domain.** Search `game/` for what belongs to an adapter or the entry point: network, SDK, filesystem, environment, `print`, the clock, a JSON payload shape for the client, prompt text.
  - **Ports.** Every port is in `game/ports.py`. The port name is a game capability and each method a game action, not a vendor call. No vendor error crosses a port.
  - **Adapters (`api/`).** No game rule. Every vendor error is translated and logged. No secret in an error or a log line.
  - **Entry point (`server.py`).** Routes parse the body once, answer 400 on bad input, call one engine method, and mutate game state only under the engine's lock. No blocking vendor call on the game loop thread or in a request handler.
  - **Client contract.** A route, event or payload change updates `static/` and `docs/api.md` in the same PR.
  - **LLM output.** New Mistral calls follow `.claude/rules/structured-llm-output.md`.
  - **Names, signatures, docstrings.** Full-word game names, one concept per name across server and client, at most two positional parameters on new functions, interface docstrings where the signature does not say it all, tuning numbers in `game/settings.py`.
  - **Tests.** Domain tests build their world by hand and use fakes; no network or audio device; a rule is tested at one layer; a bug fix comes with its test.

  When the prompt gives no gate results, run `make check` from the repository root (and the `ub-mode` gates when installed: `uv run --script ~/.claude/skills/ub-mode/scripts/quality.py --base origin/<target> --tests tests`). A breach the PR introduces is a 🟠 `!` finding; a pre-existing breach in a touched file is a 🟡 `#` finding.
- When the PR changes a Mistral or ElevenLabs integration (model name, SDK call, response format), compare it with the vendor's current documentation. A PR that builds on a deprecated model or API gets a finding.
- Full mode only: the repo's standards are the rules above. State the requirement level applied (the rules in `.claude/rules/` on what the PR adds or changes) in the review file instead of asking for one.

---

## Step 3 — Review (read-only mode)

One careful pass over the whole diff, the changed code and its dependencies, then one pass commit by commit when the branch has more than one commit (`git log --reverse origin/<target>..<branch>`, then `git show <sha>` for each).

- Check every rule of Step 2. A focus list or a list of decisions given by the orchestrator tells what not to report; it never removes a rule from the check.
- Commit by commit: the message says what the diff does, and nothing the diff no longer does after later fixups; a type or a function does not move twice across the branch; each commit stands on its own (imports resolve, its tests pass).
- Docs and prompts: compare every doc, rule, skill or prompt the PR adds or changes with the code at the head of the branch (names, routes, commands, behaviours).
- Be extra mindful of afferent and efferent dependencies: how the change affects other parts of the codebase, `static/` included.
- A finding is blocking only when the PR introduces or activates the issue. A pre-existing issue is reported as contextual information, not as a blocking finding, unless the PR changes its reachability, severity, or impact.
- Validate each finding yourself against the code before keeping it. Reject findings that cannot be supported by concrete evidence from the codebase.

---

## Review table

Used by both modes.

| Criticity | Problem Description | Location | Condition | Impact | Changes Required | PR Comment Branding |
|-----------|---------------------|----------|-----------|--------|------------------|----------------------|
| 🔴, 🟠, 🟡 | What is technically wrong. | File path and relevant symbol, function, class, or configuration entry. | The condition(s) under which the issue occurs. | The concrete effect of the issue. | Nature of the required change, without code. | `!!!` Cross-cutting impact · `!` Blocking · `#` Comment/knowledge sharing · `?` Question/clarification · `*` Nice to have · `**` Super nice to have |

Use ASD-STE100 Simplified Technical English for all descriptions. Do not use `--` in prose. No qualitative feedback: strictly factual.

When the PR adds or changes application code, put an **Imports by module** block after the table: one line per module the PR adds or changes, with its layer and the project modules it imports. A line that breaks the import direction points to its finding.
