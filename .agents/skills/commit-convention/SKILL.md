---
name: commit-convention
description: Format git commit messages to match this user's established house style (Conventional Commits, English, imperative, no trailing period). Use whenever you are about to run `git commit`, draft a commit message, or the user asks you to write/fix/rewrite a commit message — in any repo, regardless of what language that repo's own past commits happen to use.
---

# Commit message convention

## Format

```
type(scope): imperative summary
```
Follow conventional commits, but with a few tweaks to match this user's established house style:

- **type**: one of `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore` — pick the one that
  matches what actually changed, not the file type touched.
- **scope**: optional, one lowercase word naming the area/module/feature (e.g. `notion`, `sales`,
  `staffing`, `slack`). Omit it when the change is repo-wide or doesn't fit one area — plenty of
  history commits skip it (`docs: ...`, `feat: add experiences to looker`).
- **summary**: imperative mood ("add", "fix", "stop", "route" — not "added"/"fixes"), lowercase
  start, no trailing period. Say what the commit does, not what bug ticket it closes.

## Language

Always write commit messages in **English**, even where past commits are in French.
That's a deliberate override of what the repo's own history shows, not an oversight.

## Things to skip

- Don't append a PR number like `(#666)` — that's added automatically by the git host on
  squash-merge, never typed by hand.
- Don't add a body/footer unless the change genuinely needs explaining beyond the summary line
  (a non-obvious why, a breaking change, a linked incident). Most commits in this history are a
  single line.

## Examples

```
fix(agent): coerce a model-supplied limit before it reaches a slice
feat(slack): open the pilot to new users
refactor(notion): split the provider into api / render / tool surface
docs: clarify what the billed/staffed measures include
```
