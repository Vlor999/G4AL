# Planning workflow

These rules apply whenever Claude is about to write or update a plan file.

## Before writing the plan

1. **Ask clarifying questions first.** Identify ambiguities, hidden assumptions, and
   dependencies. Surface them as explicit questions before proposing anything.

2. **Challenge scope.** Push back on anything that can be deferred, removed, or
   simplified. A smaller plan is almost always better.

3. **Explore at least two approaches** in conversation. Name the trade-offs briefly,
   then recommend one. Do this in chat, not in the plan file.

4. **Impact inventory.** When the change deletes, merges, moves, renames or re-keys
   something, enumerate every reference to it from the repo — schema, code, jobs,
   config, every surface that reaches the same write — and say what happens to
   each. From a search, not from memory. Do this in chat, not in the plan file:
   the plan records the decisions it led to.

5. **Adversarial review.** Once you have a draft approach, hand it to a fresh
   Claude instance (spawn a subagent) as an independent challenger, with the
   impact inventory: its first job is to complete it. Surface any blockers it
   raises and address them before writing the plan file.

6. **Write the plan only after direction is agreed.** The plan records the chosen
   path, not the deliberation that led to it.

## Plan file rules

- **Max 100 lines.** If you are over, cut — remove rationale, collapse steps, drop
  sections that don't affect execution.
- **No option comparisons in the file.** Rejected alternatives stay in the
  conversation.
- **No rationale for choices.** Record what to do and why the problem matters, not
  why you didn't pick something else.
- Structure: Context → Approach → Files to modify → Verification. Skip sections
  that don't apply.
- **Run the prose through the `writing` skill** before handing the plan over.
