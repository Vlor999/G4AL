---
name: rules-review
description: |
  Audit the current branch's diff against G4AL's coding rules (.claude/rules/),
  using a fresh-context sub-agent so the reviewer has no recall of the
  conversation that produced the changes. Trigger phrases: "review my changes
  against the rules", "audit this branch", "check the diff", "is this ready
  for PR". Invoke proactively after a non-trivial implementation lands locally
  and before opening a PR.
allowed-tools:
  - Bash
  - Agent
---

# Rules review

Spawns one fresh-context sub-agent that audits the current branch against the
rules in `.claude/rules/`. It does not see the conversation that produced the
changes: a reviewer with cold eyes catches what the author rationalized away.

## Steps

1. Compute the diff:

   ```bash
   git fetch origin main --quiet
   git diff origin/main...HEAD --stat
   git diff origin/main...HEAD
   git status --short
   ```

   If the working tree is dirty, also include `git diff` and say which parts are
   committed and which are not.

2. Run the gates and keep their output for the reviewer: `make check`.

3. Spawn the review sub-agent with `Agent` (`general-purpose`, model `opus`) and
   the prompt below. Pass the raw diff, never a summary of it.

4. Surface the findings verbatim, grouped by severity.

5. Offer to fix the BLOCKER and HIGH findings. Do not auto-fix: the user decides.

## Sub-agent prompt

```
You are reviewing a branch of G4AL (voice-controlled 2D survival game: Flask +
Socket.IO server, pure game simulation in game/, Mistral Voxtral and ElevenLabs
adapters in api/, HTML5 canvas client in static/) before it becomes a PR. You have
NO context from the conversation that produced this diff. Do not rationalize the
author's choices; push back on anything questionable.

Read AGENTS.md and every file under .claude/rules/ first, with the Read tool.

Gate output (make check):
<GATES>

Diff:
<DIFF>

Produce a punch list grouped by severity. For each finding: file:line, the rule
it breaks (if any), one sentence of explanation, a concrete fix.

- BLOCKER: security (secret, unvalidated input, server bound to all interfaces by
  default), broken or skipped tests, failing gate, broken client/server contract,
  game state mutated outside the loop's lock.
- HIGH: breach of an explicit rule: I/O or vendor import in game/, game rule in
  server.py or static/, prompt-and-parse LLM output, bare str for a fixed set,
  abbreviated names, file pushed past ~500 lines, dead code left behind.
- MEDIUM: judgment calls (a shallow module, repeated error handling, a missing
  test for a new branch). Mark "intent unclear" when you cannot tell.
- LOW: nits, naming alternatives, comment polish.

Also check that a delete, rename or move accounts for every reference, static/
included: search the repo, do not take the diff's word for it.

End with one verdict line: PASS, PASS WITH NITS, or BLOCK.
Keep the report under 300 lines.
```

## When not to use

- Trivial commits (typo, dependency bump) and documentation-only changes.
- When the user asks for another review flow (`/code-review`, `/security-review`).
