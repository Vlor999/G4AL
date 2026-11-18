---
type: testing
title: Testing and quality gates
description: How the pytest suite is organised around fakes of the ports, and which checks make check and CI run, including the coverage floor, import contract, strict typing and dead-code scan.
tags: [testing, quality, ci, pytest, lint]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:30:24.405Z
sources:
  - id: openwiki-source-164e2da859b5277df81c7d94
    resource: repo://.github/workflows/ci.yml
  - id: openwiki-source-4d1645cb6317345817452838
    resource: repo://.pre-commit-config.yaml
  - id: openwiki-source-012f2c78e3b1446dfc35803f
    resource: repo://Makefile
  - id: openwiki-source-f5dba60ad5d28b73ea34e2b1
    resource: repo://mypy.ini
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-f0a6e7dc03522b2682f88655
    resource: repo://tests/conftest.py
  - id: openwiki-source-da1cc862f5a540f793502703
    resource: repo://tests/e2e/conftest.py
  - id: openwiki-source-467f6eebd2ab90c10a9061f8
    resource: repo://tests/fakes.py
  - id: openwiki-source-934e5393ac0ca4f9a0e9a538
    resource: repo://vulture_allowlist.py
generated: { by: "claude-code", at: "2026-11-18T09:30:24.405Z" }
---

# Testing and quality gates

`make check` runs what CI runs: format check, lint plus the import contract, strict type check, dead-code scan, then tests with coverage. It is the verification for a change; the server is not started to verify one.

## Gates

| Make target | Tool | What it enforces |
|---|---|---|
| `format-check` | `ruff format --check` | Formatting, line length 100 |
| `lint-check` | `ruff check`, `lint-imports` | Rule set in `ruff.toml` (pycodestyle, pyflakes, isort, bugbear, bandit, naming, complexity and more); the `game/` import contract in `pyproject.toml` |
| `type-check` | `mypy` | `strict = True` over `game`, `api`, `server` and `main.py`; tests may be untyped |
| `dead-code` | `vulture` | Unused code in `game`, `api`, `server`, `main.py` and `vulture_allowlist.py` |
| `test` | `pytest --cov` | Suite plus a coverage floor |

The coverage floor is `fail_under = 83` over `game`, `api` and `server` with branch coverage. The import contract is described in [System overview](../architecture/system-overview.md).

## Vulture and its allowlist

Vulture reads attribute access, not subscription. `vulture_allowlist.py` lists the `Arrow` keys (`fromX`, `fromY`, `toX`, `toY`, `frame`, `totalFrames`, `team`) and the storage snapshot key `houseCount`, which are read by dict subscription in `server/` or by the client through the state JSON. Route and Socket.IO handler decorators are ignored because the frameworks call them.

## Test layout

- `tests/` holds unit tests per domain module (`test_npc.py`, `test_archer.py`, `test_storage.py`, `test_pathfinding.py`, `test_orders.py`, and so on) plus adapter tests (`test_interpreter.py`, `test_tts.py`).
- `tests/conftest.py` provides `build_map`, which draws a `GameMap` from ASCII rows (`.` grass, `:` dirt, `s` sand, `~` water), so domain tests build their world by hand.
- `tests/fakes.py` has fakes of the ports: `ScriptedOrderInterpreter` answers with fixed orders, a refusal or an error, and `RecordingSpeaker` records voice lines.
- `tests/e2e/` builds a `GameEngine` with those fakes and serves it through `create_app` and Flask's test client: HTTP contract (`test_http_api.py`), voice order flow (`test_voice_orders.py`) and the tick and loop with a fake socket (`test_game_loop.py`). No network, audio device or running server is involved.

See [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md) and [Voice order flow](../workflows/voice-order-flow.md) for what these tests exercise.

## Pre-commit and CI

Pre-commit runs file hygiene hooks, `ruff` check and format, `gitleaks`, and local `mypy` and `vulture` hooks. The CI workflow has a quality job that runs the same make targets after `uv sync --locked`, and a security job that runs gitleaks and `pip-audit` on the exported lockfile. A bug fix comes with the test that would have caught it.

## Related pages

- [Quickstart](../quickstart.md)
- [Adapters](../systems/adapters.md)
