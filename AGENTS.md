# G4AL

Voice-controlled top-down 2D survival game. The player holds a key and speaks an
order; Mistral Voxtral turns the audio into structured NPC orders; NPCs carry them out
(chop wood, mine rock, build, farm, defend) and answer with an ElevenLabs voice line.
A Flask + Socket.IO server runs the simulation at 60 FPS and pushes the state to an
HTML5 Canvas client every 3rd tick (~20 Hz).

## Layout

| Path | Role |
|---|---|
| `game/` | Domain: pure simulation (map, NPCs and action queue, fauna, resources, storage, pathfinding, tuning in `settings.py`). No I/O. |
| `api/` | Adapters: Mistral Voxtral (`interpreter.py`), ElevenLabs + pygame mixer (`tts.py`), structured logs (`logger.py`), NPC personalities (`roster.py`). |
| `server/` | Entry point: `app.py` (`create_app`, `main`: loads `.env`, builds the adapters), `engine.py` (`GameEngine` and its game loop thread), `routes.py` (Flask routes, Socket.IO), `serialization.py` (client JSON). |
| `main.py` | Starts the server (`server.app.main`). |
| `static/` | Browser client: classic scripts sharing globals, loaded in order by `index.html`, no build step (`game.js` entry, `map_image.js`, `renderer.js`, `input.js`, `ptt.js`, `ui.js`, `sprites.js`). |
| `tests/` | Pytest suite. |
| `scripts/` | Standalone tools run with `uv run --script` (PEP 723), outside the game: `asset_inventory.py` writes `docs/assets.md`. |
| `docs/` | [Architecture](docs/architecture.md), [client/server contract](docs/api.md), [decisions](docs/adr/). |
| `openwiki/` | Generated repository wiki, start at the [quickstart](openwiki/quickstart.md). Refresh it by running the `openwiki` skill in `update` mode after significant merges into `dev`; no scheduled workflow. |

## Commands

```bash
make install       # uv sync + pre-commit hooks
make run           # start the server on http://127.0.0.1:8000
make check         # format, lint + import contract, mypy --strict, vulture, pytest + coverage (what CI runs)
make format-fix lint-fix
uv run pytest tests/test_storage.py -k capacity   # one test
```

Python 3.11, dependencies with `uv` only (`uv add`, `uv add --dev`). Never run the
server to verify a change unless asked: `make check` is the verification.

## Rules

`.claude/rules/` is loaded automatically by Claude Code; other agents read it here:

- [architecture.md](.claude/rules/architecture.md): layers, injection, tests, quality gates.
- [language.md](.claude/rules/language.md), [naming.md](.claude/rules/naming.md),
  [typing.md](.claude/rules/typing.md): English code, full-word names, enums for fixed sets.
- [file-organization.md](.claude/rules/file-organization.md),
  [dead-code.md](.claude/rules/dead-code.md): one concern per file, ~500 lines, delete unused code.
- [security.md](.claude/rules/security.md), [server-style.md](.claude/rules/server-style.md):
  secrets, input validation, thread safety of the game loop.
- [structured-llm-output.md](.claude/rules/structured-llm-output.md): constrain Mistral
  output with a schema, never parse prose.
- [git-workflow.md](.claude/rules/git-workflow.md),
  [planning-workflow.md](.claude/rules/planning-workflow.md),
  [subagents.md](.claude/rules/subagents.md).

Third-party APIs (Mistral, ElevenLabs): read the vendor's current docs before
changing an integration; model names and SDK signatures move fast.

## Skills

In `.agents/skills/` (linked from `.claude/skills/`): `mr-review` (review a PR against
the rules, multi-agent in full mode), `rules-review` (quick audit of a branch), `commit-convention`, `writing`, `worktree`, `handoff`, `grill-me`,
`grill-with-docs`, `improve-codebase-architecture`, `request-refactor-plan`,
`ubiquitous-language`, `openwiki`.

## Gotchas

- The game loop runs in its own thread; routes and Socket.IO handlers mutate state
  through `GameEngine` only.
- Durations and speeds in `game/settings.py` are in frames (60 FPS), not seconds.
- `ELEVENLABS_API_KEY` is optional: without it NPCs do not speak, and nothing fails.
- Logs go to `logs/` (git-ignored) as JSONL with cost and token usage per call.

<!-- OPENWIKI:START -->

## OpenWiki

This repository has a generated `openwiki/` evidence index. It is optional just-in-time context, not required startup reading.

- Treat source code and tests as authoritative. A brief's unknowns and review items are verification gaps, not automatic requirements.
- Prefer the narrowest quiet validation that proves the changed behavior. Preserve complete failure output.

The scheduled OpenWiki GitHub Actions workflow refreshes the repository wiki. Do not hand-edit generated OpenWiki pages unless explicitly asked; prefer updating source code/docs and letting OpenWiki regenerate.

<!-- OPENWIKI:END -->
