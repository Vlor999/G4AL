---
type: operations
title: Running and configuration
description: How to start the G4AL server, which environment variables it reads, what is optional, where logs go and how audio playback is set up.
tags: [operations, configuration, environment, logging]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:41:00.050Z
sources:
  - id: openwiki-source-5a30db6dbee6aab6793cc16a
    resource: repo://api/interpreter.py
  - id: openwiki-source-b7fcb6ba7b5ef12e584d14ba
    resource: repo://api/logger.py
  - id: openwiki-source-18da8bfe4ae2cbf4ece58cf2
    resource: repo://api/tts.py
  - id: openwiki-source-141c86ea716204370c1b7a2d
    resource: repo://server/app.py
generated: { by: "claude-code", at: "2026-11-18T09:41:00.050Z" }
---

# Running and configuration

## Start

```bash
make install   # uv sync + pre-commit hooks
cp .env.example .env
make run       # uv run python main.py
```

`main.py` imports `server.app.main` lazily and calls it. The server then serves the client and the API on `http://127.0.0.1:8000`. See [System overview](../architecture/system-overview.md) for what `main()` wires together.

## Environment

| Variable | Read by | Effect |
|---|---|---|
| `MISTRAL_API_KEY` | `VoxtralOrderInterpreter` | Read when the first command arrives, not at startup. Without it the call raises `OrderInterpretationError("MISTRAL_API_KEY is not set")`, the command is dropped and the game is unchanged. |
| `ELEVENLABS_API_KEY` | `TTSEngine` | Optional. Without it no worker thread starts and every voice line is dropped silently. The code logs a warning, but the current log sinks drop it (#50). |
| `G4AL_HOST` | `server/app.py` | Bind address, default `127.0.0.1`. Setting it exposes the server on a network. |

`.env` is loaded once by `main()` from the project root, before the adapters are built, because `TTSEngine` reads its key from the environment at construction. `.env.example` lists the two keys with placeholders.

## Audio

`main()` sets `SDL_VIDEODRIVER=dummy`, then calls `pygame.init()` and `pygame.mixer.init()`. pygame is used only for audio: `TTSEngine` plays each mp3 clip through `pygame.mixer.music` and waits until it ends so lines do not overlap. In tests the playback function is injected instead. See [Adapters](../systems/adapters.md).

## Logs

`api/logger.py` creates a `logs/` directory at the repository root (git-ignored) and, per session, writes a human-readable `.log` and a structured `.jsonl` file, both rotated at 50 MB. Only records bound with an `event` extra reach these sinks. The pipeline logger tracks timing, token usage and estimated cost for Voxtral and ElevenLabs calls. `GameEngine.stop()` closes it.

## Shutdown

`main()` catches `KeyboardInterrupt`, then stops the engine loop and closes the speaker in a `finally` block.

## Related pages

- [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md) for origin checks and limits.
- [Testing and quality gates](../testing/quality-gates-and-tests.md)
