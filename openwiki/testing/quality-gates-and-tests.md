---
type: testing
title: Testing and quality gates
description: How the pytest suite is organised around fakes of the ports, and which checks make check and CI run, including the coverage floor, both import contracts, strict typing and the dead-code scan.
tags: [testing, quality, ci, pytest, lint]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T15:38:15.273Z
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
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# Testing and quality gates

`make check` runs what CI runs: format check, lint plus the import contracts, strict type check, dead-code scan, then tests with coverage. It is the verification for a change; the server is not started to verify one.

## Gates

| Make target | Tool | What it enforces |
|---|---|---|
| `format-check` | `ruff format --check` | Formatting, line length 100 |
| `lint-check` | `ruff check`, `lint-imports` | Rule set in `ruff.toml` (pycodestyle, pyflakes, isort, bugbear, bandit, naming, complexity and more); the two import contracts in `pyproject.toml` |
| `type-check` | `mypy` | `strict = True` over `game`, `api`, `server` and `main.py` (`mypy.ini`); tests may have untyped functions |
| `dead-code` | `vulture` | Unused code in `game`, `api`, `server`, `main.py` and `vulture_allowlist.py`, at 60% confidence |
| `test` | `pytest --cov` | Suite plus a coverage floor, with terminal and XML reports |

The coverage floor is `fail_under = 83` over `game`, `api`, `server` and `scripts`, with branch coverage.

The two import contracts are described in [System overview](../architecture/system-overview.md):

- `game` imports no adapter, entry point or I/O library.
- The `game` sub-packages depend downward only.

## Vulture and its allowlist

Vulture reads attribute access, not subscription. `vulture_allowlist.py` lists names it would report although they are read where it cannot see:

- the `Arrow` keys (`fromX`, `fromY`, `toX`, `toY`, `frame`, `totalFrames`, `team`), read by subscription in `server/`;
- the storage snapshot key `houseCount`, read by the client through the state JSON;
- the `ArcherName` and `WildArcherName` members, read by iterating the enums to build the name pools.

Route and Socket.IO handler decorators are ignored because the frameworks call them.

## Test layout

- `tests/` is flat and holds unit tests per module: domain (`test_npc.py`, `test_archer.py`, `test_wild_archer.py`, `test_fauna.py`, `test_storage.py`, `test_pathfinding.py`, `test_map_generation.py`, `test_simulation.py`, `test_orders.py`, and so on), adapters (`test_interpreter.py`, `test_tts.py`, `test_logger.py`, `test_model_catalog.py`), entry point (`test_providers.py`, `test_model_selection.py`, `test_host_allowlist.py`, `test_serialization.py`) and `test_asset_inventory.py` for the script.
- `tests/conftest.py` provides:
  - `build_map`, which draws a meadow `GameMap` from ASCII rows (`.` grass, `:` dirt, `s` sand, `~` water), so domain tests build their world by hand;
  - `clock_at(n)`, a `WorldClock` already advanced `n` frames, for grace-period tests;
  - `llm_end_records`, which captures the `llm_end` log records.
- `tests/fakes.py` has fakes of the ports:
  - `ScriptedOrderInterpreter` answers typed and spoken commands with fixed orders, a refusal or an error, and records each command and model id;
  - `RecordingSpeaker` records voice lines;
  - `build_model_selection` wires the interpreter as the Mistral provider, with or without a voice adapter;
  - `run_now` runs the engine's background work on the calling thread.
- `tests/e2e/` builds a `GameEngine` with those fakes and serves it through `create_app` and Flask's test client, with `localhost:8000` as `SERVER_NAME` so the `Host` check passes:
  - `test_http_api.py` drives the HTTP contract;
  - `test_command_orders.py` drives typed and spoken commands, chat, refusals and model switches;
  - `test_game_loop.py` drives the tick and loop with a fake socket.

  No network, audio device or running server is involved.

See [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md) and [Voice and typed order flow](../workflows/voice-order-flow.md) for what these tests exercise.

## Pre-commit and CI

- **Pre-commit** runs file hygiene hooks, `ruff` check and format, `gitleaks`, and local `mypy` and `vulture` hooks.
- **CI quality job** runs the same make targets after `uv sync --locked`.
- **CI security job** runs gitleaks and `pip-audit` on the exported lockfile.

Other workflows run CodeQL, an optional Claude security review, and a check that PRs into `main` come from `dev`. A bug fix comes with the test that would have caught it.

## Related pages

- [Quickstart](../quickstart.md)
- [Adapters](../systems/adapters.md)
- [LLM models and providers](../systems/llm-models-and-providers.md)
