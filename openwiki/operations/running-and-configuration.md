---
type: operations
title: Running and configuration
description: How to start the G4AL server, which environment variables it reads and when they stop the start, what is optional, where logs go and how audio playback is set up.
tags: [operations, configuration, environment, logging]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T15:38:15.273Z
sources:
  - id: openwiki-source-b7fcb6ba7b5ef12e584d14ba
    resource: repo://api/logger.py
  - id: openwiki-source-18da8bfe4ae2cbf4ece58cf2
    resource: repo://api/tts.py
  - id: openwiki-source-141c86ea716204370c1b7a2d
    resource: repo://server/app.py
  - id: openwiki-source-be5f2d227c84deca728731ae
    resource: repo://server/constants.py
  - id: openwiki-source-1c24919bb4b6d54036334bad
    resource: repo://server/host_allowlist.py
  - id: openwiki-source-fbf7171f46d33a488a6bdda0
    resource: repo://server/providers.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# Running and configuration

## Start

```bash
make install   # uv sync + pre-commit hooks
cp .env.example .env
make run       # uv run python main.py
```

`main.py` imports `server.app.main` lazily and calls it. The server then serves the client and the API on port 8000 and prints the URL a browser should open (`http://localhost:8000` on loopback). See [System overview](../architecture/system-overview.md) for what `main()` wires together.

## Environment

`.env` is loaded once by `main()` from the project root, before anything else, because the startup checks and `TTSEngine` read the environment. `.env.example` lists every variable with a placeholder.

| Variable | Read by | Effect |
|---|---|---|
| `MISTRAL_API_KEY` | `read_startup_models` | Key of the Mistral provider. When the start model is a Mistral model and the key is unset or blank, the server exits at startup with `MISTRAL_API_KEY is not set: the mistral provider needs it`. Only models whose provider key is set can be picked in game. |
| `G4AL_LLM_PROVIDER` | `read_startup_models` | Provider of the start model, default `mistral`. An unknown name exits at startup and lists the known ones. |
| `G4AL_LLM_MODEL` | `read_startup_models` | Catalog id of the start model. Unset, the provider's default model is used (`voxtral-small-latest` for Mistral, the one that keeps push-to-talk). An unknown id exits at startup and lists the known ones. |
| `ELEVENLABS_API_KEY` | `TTSEngine` | Optional. Without it no worker thread starts and every voice line is dropped. A `tts_disabled` warning reaches the console and log files. |
| `G4AL_HOST` | `served_host_from_environment` | Bind address, default `127.0.0.1`. It also sets which `Host` headers are accepted. A link-local address with a zone id (`fe80::1%en0`) exits at startup. |

The models, their providers and how the picker works are on [LLM models and providers](../systems/llm-models-and-providers.md).

## Network exposure

The server binds to loopback by default. Setting `G4AL_HOST` to a network address exposes it; players then open that address. Brackets are stripped and IPv6 addresses compressed. The server answers only requests whose `Host` is allowed:

| `G4AL_HOST` | Allowed `Host` (port 8000) |
|---|---|
| unset, `127.0.0.1`, `localhost`, `::1` | `localhost`, `127.0.0.1`, plus the address itself |
| `0.0.0.0`, `::` | `localhost`, `127.0.0.1` only: a wildcard bind accepts loopback only |
| any other address | that address only |

Other requests get `403 {"error": "host not allowed"}`. See [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md).

## Audio

`main()` sets `SDL_VIDEODRIVER=dummy`, then calls `pygame.init()` and `pygame.mixer.init()`. pygame is used only for audio: `TTSEngine` plays each mp3 clip through `pygame.mixer.music` and waits until it ends so lines do not overlap. In tests the playback function is injected instead. See [Adapters](../systems/adapters.md).

## Logs

`main()` calls `use_pipeline_sinks()`, which removes loguru's default sink and adds three: a coloured stderr sink at INFO, and per session a human-readable `.log` and a structured `.jsonl` file under `logs/` (git-ignored), both at DEBUG and rotated at 50 MB. Every sink keeps only records bound with an `event` extra. Importing `api/logger.py` adds no sink.

The `PipelineLogger` that `main()` builds tracks timing, token usage, audio seconds and estimated cost for each LLM call at the called model's prices, and the character cost of each ElevenLabs call. Logs hold transcripts of typed commands, orders and costs, never audio or keys; TTS error texts have the ElevenLabs key masked.

## Shutdown

`main()` catches `KeyboardInterrupt`, then in a `finally` block stops the engine loop, closes the speaker and closes the pipeline logger, which writes the `session_end` totals.

## Related pages

- [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md) for origin checks and limits.
- [Testing and quality gates](../testing/quality-gates-and-tests.md)
