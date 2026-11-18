# Contributing

## Setup

```bash
make install          # uv sync + pre-commit install
cp .env.example .env  # add your Mistral (and optionally ElevenLabs) key
make run
```

Optional, for the `openwiki` MCP server declared in `.mcp.json`:
`npm install --global openwiki@0.5.2`.

## Workflow

1. Branch from `dev`: `<type>/<slug>` (`feat/archer-patrol`).
2. Write the change and its tests. The rules in [`.claude/rules/`](.claude/rules/) apply
   to humans and agents alike; [AGENTS.md](AGENTS.md) is the entry point.
3. `make check` must pass (format, lint, `mypy --strict`, vulture, tests). The
   pre-commit hooks run the fast part of it plus `gitleaks` on every commit.
4. Commit with Conventional Commits in English (`feat(npc): add patrol action`),
   atomic commits in dependency order.
5. Open a PR against `dev` with the template. CI must be green before merge. Pull
   `dev` in with a rebase, never a merge commit.
6. Releases go from `dev` to `main` through a PR from `dev`, merged with a merge
   commit so `dev` stays an ancestor of `main`.

## Wiki

`openwiki/` is a generated wiki of the repository; start at
[`openwiki/quickstart.md`](openwiki/quickstart.md). Do not edit its pages by hand. After
a significant merge into `dev` (a new system, a changed contract, a moved module), run
the `openwiki` skill in `update` mode from a branch and commit the result as
`docs(wiki): update the repository wiki`. There is no scheduled workflow, and the managed OpenWiki block in
`AGENTS.md` that mentions one does not apply to this repository. Refresh the wiki with
`update` only and never re-run `init`: `init` re-creates
`.github/workflows/openwiki-update.yml`. The skill
needs `npm install --global openwiki@0.5.2` and the `openwiki` MCP server of `.mcp.json`.

## Security review

The `Security review` workflow runs
[claude-code-security-review](https://github.com/anthropics/claude-code-security-review)
on every non-draft PR opened from this repository and comments the findings on the
diff lines. It needs the `ANTHROPIC_API_KEY` repository secret (Settings → Secrets
and variables → Actions). Project-specific checks live in
[`.github/security-review/scan-instructions.txt`](.github/security-review/scan-instructions.txt).
The action is not hardened against prompt injection, so it skips fork PRs; keep
"Require approval for all external contributors" on for Actions.

## Coding standards in short

- `game/` is pure: no Flask, Mistral, ElevenLabs, pygame, file or network access.
- Full-word English names, enums for fixed sets, full type annotations.
- Files under ~500 lines, one concern per file.
- A bug fix comes with the test that would have caught it.
- Dead code is deleted, not commented out.

## Branch protection

`dev` and `main` are protected by repository rulesets. Both take changes through a
pull request only, with 1 approving review, the `CI` checks (quality and security
jobs) and CodeQL required to pass, no force push and no deletion.

- `dev`: feature branches merge with squash or rebase; linear history.
- `main`: only PRs from `dev` (the `Main source branch` check fails otherwise),
  merged with a merge commit.
- Repository admins can bypass both rulesets.
