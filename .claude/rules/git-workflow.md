# Git workflow

- **Never commit directly to `main`.** Work on a branch, open a PR.
- **Branch names**: `<type>/<slug>` (`feat/archer-patrol`, `fix/pathfinding-diagonal`),
  or `<ticket>/<slug>` when there is an issue.
- **Commits** follow the `commit-convention` skill: Conventional Commits, English,
  imperative, no trailing period. Atomic and in dependency order.
- **Rebase, never merge**, to pull `main` into a branch:
  `git fetch origin && git rebase origin/main`, then `git push --force-with-lease`.
- **Never skip hooks (`--no-verify`)** unless the user explicitly asks. A failing
  pre-commit hook is fixed at its cause, then a new commit is made.
- **PR body**: "Intention / Choices and points of attention". It never asks a question:
  an open decision is settled with the user before the PR is opened.
- **CI is green before merge.** A red check is fixed, not re-run until it passes.
