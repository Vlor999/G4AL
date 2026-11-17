---
name: commit-convention
description: Format git commit messages for G4AL (Conventional Commits, English, imperative, no trailing period). Use whenever you are about to run `git commit`, draft a commit message, or rewrite one.
---

# Commit message convention

## Format

```
type(scope): imperative summary

Optional body: why the change is needed, when the diff does not say it.

Co-Authored-By: ... (when an agent wrote the commit)
```

- **type**: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `style`, `build`, `ci`,
  `chore`. Pick the one that matches what changed, not the file type touched.
- **scope**: optional, one lowercase word naming the area: `game`, `npc`, `map`,
  `storage`, `server`, `api`, `interpreter`, `tts`, `static`, `deps`, `agents`, `ci`.
  Omit it when the change is repo-wide.
- **summary**: imperative mood ("add", "fix", "split"), lowercase start, no trailing
  period, under ~72 characters. Say what the commit does.

## Body

Add a body when the summary does not carry the why: a behaviour change hidden in a
refactor or a typing pass, a non-obvious choice, a breaking change in the
client/server contract (`docs/api.md`). A behaviour change always gets its own commit
or a body line that names it.

## Atomic commits

One logical change per commit, in dependency order, each one passing `make check`.
Formatting, refactors and behaviour changes go in separate commits.

## Things to skip

- No PR number like `(#12)`: the host adds it on squash merge.
- No French, even in a French conversation.

## Examples

```
fix(npc): return the enqueue result from Archer so archers answer orders
refactor(server): move order application from GameEngine to game/
feat(api): constrain Voxtral output with a JSON schema
docs: document the ~20 Hz state push in the client contract
```
