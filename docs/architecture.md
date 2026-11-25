# Architecture

## Runtime

```
Browser (static/: Canvas renderer, input, push-to-talk, chat)
   │  HTTP: /api/state, /api/action, /api/select, /api/move,
   │        /api/discard, /api/dismiss_storage, /api/audio, /api/command,
   │        /api/model
   │  Socket.IO: state push every 3rd tick (~20 Hz)
   ▼
server/: app.py (create_app, main), routes.py (Flask + Socket.IO),
         engine.py (GameEngine, game loop thread, 60 FPS), serialization.py
   ├── game/        pure simulation: world, resources, combat, npcs, fauna, orders
   ├── api/interpreter.py  text or WAV → Mistral → NPC orders (worker thread)
   ├── api/tts.py          voice line → ElevenLabs → pygame mixer (worker thread)
   └── api/logger.py       JSONL logs with timing, tokens and cost
```

## Command flow

1. `static/ptt.js` records while the key is held, encodes a WAV and posts it to
   `/api/audio`; `static/chat.js` posts a typed command to `/api/command`, and the
   model picked in its list to `/api/model`.
2. `GameEngine.send_audio_command` or `send_text_command` reads the selected model
   (`server/model_selection.py`, entry point state behind its own lock), adds the
   command to the chat and hands it to a worker thread, which calls the injected port
   (`game/ports.py`) with that model's id: `VoiceOrderInterpreter` for audio (only a
   model that hears audio has one), `TextOrderInterpreter` for text. A model switch
   therefore applies from the next command. The Mistral adapter,
   `api.interpreter.MistralOrderInterpreter`, makes one call per command with the
   system prompt and the NPC roster of `api/order_contract.py`: multimodal for audio,
   text for a typed command. The model must answer by calling the
   `give_npc_orders` function once (`tool_choice="any"`,
   `parallel_tool_calls=False`), whose JSON schema takes its actions from
   `game.orders.orders.VOICE_ORDER_ACTIONS`: every `ActionType` but `move_to`, whose target
   tile a voice order does not carry (the player gives it with a right-click). The
   adapter validates the arguments into `game.orders.orders.NpcOrder` values
   (`api.order_contract.parse_orders`, shared by every provider). Mistral
   documents audio input with a forced tool call, but not with
   `parallel_tool_calls=False`; that combination is untested against the live API.
   The safety net is the adapter: an answer that still holds several
   `give_npc_orders` calls has their orders merged in call order, duplicates
   included. An answer that breaks this contract is returned as
   `CommandRefused` with a `RefusalReason`, and the game log shows
   `Order refused: <reason>`. One bad order refuses the whole answer: no order of
   that command is applied. A service failure is raised as
   `OrderInterpretationError`, logged on the server, and leaves the game unchanged;
   the game log shows `Command failed, try again.`, without the service's
   error text.
3. Answers queue in `GameEngine` as their worker threads finish. On its next tick the
   game loop takes every queued answer in arrival order and, for a list of orders,
   calls `game.orders.orders.apply_orders`, which enqueues the actions and returns one
   `OrderOutcome` per order (accepted, spoken).
4. `GameEngine` logs each reply, adds it to the chat (`docs/api.md` § Chat), and
   sends the spoken ones to the injected
   `VoiceLineSpeaker` port; its adapter, `api.tts.TTSEngine`, plays them in the
   background, and drops them when `ELEVENLABS_API_KEY` is not set.

## Adding an LLM provider

At startup (`server/providers.py`) the game starts on the model `G4AL_LLM_MODEL`
names, or else on the default model of `G4AL_LLM_PROVIDER` (default `mistral`). The
server exits with a message naming the variable when the provider or the model is
unknown, or when the start model's provider key is not set. The picker lists every
catalog model whose provider key is set. To add a provider:

1. Write one adapter module in `api/` that implements `TextOrderInterpreter`
   (`interpret_text`), and `VoiceOrderInterpreter` (`interpret_voice`) only if the
   provider takes audio. Send `build_system_prompt` and `ORDERS_SCHEMA` from
   `api/order_contract.py` in the vendor's structured-output shape, hand the answer's
   arguments to `parse_orders`, and translate every vendor error into
   `OrderInterpretationError`. Give it a `register_roster(npcs)` built on
   `build_roster`.
2. Add a member to `LlmProvider` (`api/model_catalog.py`), its key variable to
   `API_KEY_VARIABLES` in `server/constants.py`, and the variable to `.env.example`.
3. List its models in `MODEL_CATALOG` (`api/model_catalog.py`): id, display name,
   whether it hears audio, prices from the vendor's docs; and its default model in
   `DEFAULT_MODELS`. The logged cost of each call comes from these prices.
4. Add its `case` to `build_order_interpreters` in `server/providers.py`, with
   `voice=None` when it has no audio adapter: the client then hides push-to-talk for
   its models.

Nothing changes in `game/` or `static/`.

## Layers

See [`.claude/rules/architecture.md`](../.claude/rules/architecture.md).

`game/` is split into sub-packages that import only downward, from the top layer to
the bottom one ([ADR 0004](adr/0004-game-sub-packages.md)). `lint-imports` enforces
the order:

| Layer | Package | Holds |
|---|---|---|
| top | `game/spawning.py`, `game/simulation.py`, `game/ports.py` | the starting world, one frame of the world, the ports |
| orders | `game/orders/` | voice and direct orders, chat messages |
| actors | `game/npcs/`, `game/fauna/` | pawns, archers, their actions; sheep, cat, wild archers, fauna spawning |
| combat | `game/combat/` | arrows, target and firing tile searches |
| resources | `game/resources/` | trees, rocks, structures, wheat fields, storage |
| world | `game/world/` | map, terrain, map generation, pathfinding, dimensions, name pools, world clock |

`game/settings.py` and `game/constants.py` sit outside the layers: every package
reads them. Today
initial spawning (`game/spawning.py`), the frame step (`game/simulation.py`), order
application (`game/orders/orders.py`), storage discard and storage dismissal live in
`game/`; each HTTP route calls one public `GameEngine` method.

The world clock (`game/world/clock.py`, `WorldClock`) counts the frames since the game
started. `spawn_world` creates it, `advance_world` advances it at the end of each
frame (during the n-th frame it reads n - 1), and the wild archers read it through
`link_battlefield`. For the first
`WILD_ARCHER_GRACE_FRAMES` frames (7200, 2 minutes at 60 FPS) the wild archers ignore
the NPCs: they idle and wander but neither chase nor shoot, so the player has time to
learn the voice commands. The grace period follows the world clock, not each archer's
age, so a wild archer spawned later gets none of its own. `GameEngine._frame_count`
only paces the state push and plays no part in this rule.

A pawn that reaches a full storage keeps the part of its load that does not fit and
waits, queued orders included, until space frees or `/api/dismiss_storage` is called.

The entry point is the `server/` package:

| Module | Role |
|---|---|
| `server/app.py` | `create_app(engine, served_host=...)` builds the Flask and Socket.IO apps around an engine; `main()` loads `.env`, starts the pygame mixer, installs the log sinks (`api.logger.use_pipeline_sinks`), builds the `PipelineLogger` the adapters log their calls through, builds the adapters, injects them into `GameEngine` through the ports of `game/ports.py`, starts the game loop thread and serves on port 8000 of `G4AL_HOST` (default `127.0.0.1`). |
| `server/host_allowlist.py` | The WSGI middleware that answers 403 to a request whose `Host` is not an address the server is served at (DNS rebinding), around the Flask and Socket.IO apps. |
| `server/engine.py` | `GameEngine`: the game state behind one lock, the 60 FPS loop and the state push. |
| `server/providers.py` | Reads the start model (`G4AL_LLM_PROVIDER`, `G4AL_LLM_MODEL`) and the API keys, and builds each provider's order interpreters. |
| `server/model_selection.py` | `ModelSelection`: the models the player may pick and the selected one, with its interpreters. |
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
