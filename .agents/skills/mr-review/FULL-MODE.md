# Full mode — multi-agent review, validation, review file

Follow this after Steps 1 and 2 of [SKILL.md](SKILL.md). Before starting, check that the review file of Step 5 does not exist yet: NEVER overwrite an existing review file without user confirmation.

---

## Step 3 — Code Review

- Spawn 3 sub-agents (`model: "sonnet"`) simultaneously to review the code in parallel, they must review the whole of changes in the pull request, and provide detailed feedback on potential issues, improvements, and adherence to project rules. The goal of spawning several agent to do the same task is to select only relevant candidates for the final consolidated review.
    - Sub-agents should review the code that was changed and its dependencies
    - A finding is blocking only when the PR introduces or activates the issue. A pre-existing issue should be reported as contextual information, but must not be classified as a blocking finding unless the PR changes its reachability, severity, or impact.
    - Be extra mindful of afferent and efferent dependencies in the code. Make sure to consider how changes in the codebase can affect other parts

- Consolidate the feedback from all sub-agents into a single review table (format in SKILL.md § Review table). The rules to consolidate are as follows:
    - If 2/3 agents picked up on the issue, it will remain
    - If only 1/3 agents picked up on the issue and it is not minor (level 🔴, 🟠), spawn a new agent (`model: "opus"`) whose prompt it is to specifically debunk the issue and determine its validity. if this agent comes back with confirmation, the issue will remain; otherwise, it will be discarded.
    - If only 1/3 agents picked up on the issue and it is minor (level 🟡), it can be discarded without spawning a new agent.

---

## Step 4 — Technical Validation

Spawn a sub-agent (`model: "sonnet"`) that will verify that each issue identified in the review table is technically valid and reproducible.

- Verify each issue against the codebase and its dependencies.
- Confirm that the issue is introduced or activated by the PR.
- Reject findings that cannot be reproduced or supported by concrete evidence.
- Adjust the criticity if the actual impact differs from the initial assessment.
- Update the review table with the validated findings only.

A finding must not be retained based only on agent consensus; it must be supported by evidence from the codebase.

---

## Step 5 — Feedback

Generate a markdown file named `<source_branch>_TO_<target_branch>_review.md`, with branch names in lowercase and `/` replaced by `-`, at the root of the repo. Do not commit this file. Share it with the user for review and action.

- The content is the validated review table from Step 4, strictly factual.

Template:

```markdown
# PR Review

Source: feature/foo
Target: main
Reviewed commit: abc123
Merge base: def456

## Findings

| Criticity | Problem Description | Location | Condition | Impact | Changes Required | PR Comment Branding |
|-----------|---------------------|----------|-----------|--------|------------------|---------------------|
```
