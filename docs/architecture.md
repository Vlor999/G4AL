# Architecture

## Runtime

```
Browser (static/: Canvas renderer, input, push-to-talk)
   │  HTTP: /api/state, /api/action, /api/select, /api/move,
   │        /api/discard, /api/dismiss_storage, /api/audio
   │  Socket.IO: state push every 3rd tick (~20 Hz)
   ▼
server.py: Flask + Socket.IO, GameEngine (game loop thread, 60 FPS)
   ├── game/        pure simulation: map, NPCs, fauna, resources, storage
   ├── api/interpreter.py  WAV → Mistral Voxtral → NPC orders (worker thread)
   ├── api/tts.py          voice line → ElevenLabs → pygame mixer (worker thread)
   └── api/logger.py       JSONL logs with timing, tokens and cost
```

## Voice command flow

1. `static/ptt.js` records while the key is held, encodes a WAV and posts it to
   `/api/audio`.
2. `GameEngine.send_audio_command` hands the bytes to a worker thread, which calls
   `api.interpreter.interpret_audio_command`: one multimodal Voxtral call with the
   system prompt and the NPC roster.
3. The answer is parsed into a `CommandResponse` (one `NPCOrder` per NPC). On its next
   tick the game loop converts it into `game.orders.NpcOrder` values and calls
   `game.orders.apply_orders`, which enqueues the actions and returns one
   `OrderOutcome` per order (accepted, spoken).
4. `GameEngine` logs each reply and sends the spoken ones to `api.tts`, which plays
   them in the background.

## Layers

See [`.claude/rules/architecture.md`](../.claude/rules/architecture.md). Today
Initial spawning (`game/spawning.py`), order application (`game/orders.py`), storage
discard and storage dismissal live in `game/`; each HTTP route calls one public
`GameEngine` method. `GameEngine` still builds the client JSON and calls the
adapters directly, until the ports land (#12).

## Decisions

Architecture decisions are recorded in [`docs/adr/`](adr/), one file per decision
(`NNNN-title.md`: context, decision, consequences). The `grill-with-docs` skill
writes them.

## Known debt

Tracked on GitHub; the rules in `.claude/rules/` describe the target, these items do
not meet it yet.

- `GameEngine` calls `api.interpreter` and `api.tts` directly instead of through
  ports. `game/npc.py` (~1170 lines) and `server.py` (~570 lines) exceed the
  ~500-line budget (#5).
- Routes do not validate their bodies, no upload size limit, CORS open to any origin
  (#2).
- `api/interpreter.py` parses the LLM output from prose instead of constraining it with
  a schema (#3).
- Coverage is ~54%, weak on NPC planning and adapters (#4).
- About 40 unused functions, attributes and constants that vulture reports at 60%
  confidence; the gate runs at 80% until they are removed (#8).
- `static/renderer.js` (~950 lines) exceeds the ~500-line budget.
