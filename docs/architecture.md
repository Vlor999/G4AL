# Architecture

## Runtime

```
Browser (static/: Canvas renderer, input, push-to-talk)
   │  HTTP: /api/state, /api/action, /api/select, /api/move,
   │        /api/discard, /api/dismiss_storage, /api/audio
   │  Socket.IO: state push every 3rd tick (~20 Hz)
   ▼
server/: app.py (create_app, main), routes.py (Flask + Socket.IO),
         engine.py (GameEngine, game loop thread, 60 FPS), serialization.py
   ├── game/        pure simulation: map, NPCs, fauna, resources, storage
   ├── api/interpreter.py  WAV → Mistral Voxtral → NPC orders (worker thread)
   ├── api/tts.py          voice line → ElevenLabs → pygame mixer (worker thread)
   └── api/logger.py       JSONL logs with timing, tokens and cost
```

## Voice command flow

1. `static/ptt.js` records while the key is held, encodes a WAV and posts it to
   `/api/audio`.
2. `GameEngine.send_audio_command` hands the bytes to a worker thread, which calls the
   injected `OrderInterpreter` port (`game/ports.py`). Its adapter,
   `api.interpreter.VoxtralOrderInterpreter`, makes one multimodal Voxtral call with
   the system prompt and the NPC roster. Voxtral must answer by calling the
   `give_npc_orders` function once (`tool_choice="any"`,
   `parallel_tool_calls=False`), whose JSON schema takes its actions from
   `game.orders.VOICE_ORDER_ACTIONS`: every `ActionType` but `move_to`, whose target
   tile a voice order does not carry (the player gives it with a right-click). The
   adapter validates the arguments into `game.orders.NpcOrder` values. Mistral
   documents audio input with a forced tool call, but not with
   `parallel_tool_calls=False`; that combination is untested against the live API.
   The safety net is the adapter: an answer that still holds several
   `give_npc_orders` calls has their orders merged in call order, duplicates
   included. An answer that breaks this contract is returned as
   `CommandRefused` with a `RefusalReason`, and the game log shows
   `Order refused: <reason>`. One bad order refuses the whole answer: no order of
   that command is applied. A service failure is raised as
   `OrderInterpretationError`, logged on the server, and leaves the game unchanged;
   the game log shows `Voice command failed, try again.`, without the service's
   error text.
3. Answers queue in `GameEngine` as their worker threads finish. On its next tick the
   game loop takes every queued answer in arrival order and, for a list of orders,
   calls `game.orders.apply_orders`, which enqueues the actions and returns one
   `OrderOutcome` per order (accepted, spoken).
4. `GameEngine` logs each reply and sends the spoken ones to the injected
   `VoiceLineSpeaker` port; its adapter, `api.tts.TTSEngine`, plays them in the
   background, and drops them when `ELEVENLABS_API_KEY` is not set.

## Layers

See [`.claude/rules/architecture.md`](../.claude/rules/architecture.md). Today
initial spawning (`game/spawning.py`), the frame step (`game/simulation.py`), order
application (`game/orders.py`), storage discard and storage dismissal live in
`game/`; each HTTP route calls one public `GameEngine` method.

A pawn that reaches a full storage keeps the part of its load that does not fit and
waits, queued orders included, until space frees or `/api/dismiss_storage` is called.

The entry point is the `server/` package:

| Module | Role |
|---|---|
| `server/app.py` | `create_app(engine, served_host=...)` builds the Flask and Socket.IO apps around an engine; `main()` loads `.env`, starts the pygame mixer, installs the log sinks (`api.logger.use_pipeline_sinks`), builds the `PipelineLogger` the adapters log their calls through, builds the adapters, injects them into `GameEngine` through the ports of `game/ports.py`, starts the game loop thread and serves on port 8000 of `G4AL_HOST` (default `127.0.0.1`). |
| `server/host_allowlist.py` | The WSGI middleware that answers 403 to a request whose `Host` is not an address the server is served at (DNS rebinding), around the Flask and Socket.IO apps. |
| `server/engine.py` | `GameEngine`: the game state behind one lock, the 60 FPS loop and the state push. |
| `server/routes.py` | The HTTP routes (a blueprint that reads the engine from the app) and the Socket.IO `connect` event. |
| `server/serialization.py` | The JSON the client reads, built from the game state. |

Importing these modules starts no vendor client, game loop or audio device; the e2e
tests build an engine with fake ports and serve it through `create_app`.

## Decisions

Architecture decisions are recorded in [`docs/adr/`](adr/), one file per decision
(`NNNN-title.md`: context, decision, consequences). The `grill-with-docs` skill
writes them.

## Known debt

Tracked on GitHub; the rules in `.claude/rules/` describe the target, these items do
not meet it yet.

- `static/renderer.js` (~850 lines) exceeds the ~500-line budget.
