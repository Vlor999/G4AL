---
paths:
  - "game/**/*.py"
  - "api/**/*.py"
  - "*.py"
  - "static/**/*.js"
---

# Dead code

`uv run vulture` runs in `make check` and in CI. It catches unused names; the rules
below catch what it cannot.

## Question every branch you didn't take

Before extending a branch, check that it is reached when the game runs. If it is not,
delete it instead of growing it. "Just in case" branches rot; git history keeps them.

## Modules, assets, dependencies, env vars

When a PR removes the last user of a module, a sprite under `static/assets/`, a
dependency in `pyproject.toml` or an env var in `.env.example`, it removes them too.
(`api/voice.py`, `pyaudio` and `pillow` went this way: the browser records the audio.)

## Removing or renaming a function

Search the whole repository for its callers before it goes, `static/` included,
because the client calls the server by route and event name:
`git grep -n "<name>"`.

## Stale `# type: ignore`

`warn_unused_ignores = true` makes mypy fail on an ignore that suppresses nothing.
Remove it.

## Symptoms to watch for

- An `else:` that the game never reaches.
- A function only called by another dead function.
- A setting in `game/settings.py` nobody reads (the `COLOR_*` constants of the old
  pygame renderer are candidates).
- A route or Socket.IO event the client never calls.

When you spot one, raise it in your reply rather than silently keeping it.
