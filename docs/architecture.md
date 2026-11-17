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
2. `GameEngine.send_audio_command` hands the bytes to a worker thread, which calls the
   injected `OrderInterpreter` port (`game/ports.py`). Its adapter,
   `api.interpreter.VoxtralOrderInterpreter`, makes one multimodal Voxtral call with
   the system prompt and the NPC roster, and returns `game.orders.NpcOrder` values; a
   failure is raised as `OrderInterpretationError`, logged, and leaves the game
   unchanged.
3. On its next tick the game loop calls `game.orders.apply_orders`, which enqueues the
   actions and returns one `OrderOutcome` per order (accepted, spoken).
4. `GameEngine` logs each reply and sends the spoken ones to the injected
   `VoiceLineSpeaker` port; its adapter, `api.tts.TTSEngine`, plays them in the
   background, and drops them when `ELEVENLABS_API_KEY` is not set.

## Layers

See [`.claude/rules/architecture.md`](../.claude/rules/architecture.md). Today
Initial spawning (`game/spawning.py`), order application (`game/orders.py`), storage
discard and storage dismissal live in `game/`; each HTTP route calls one public
`GameEngine` method. `server.py` builds the adapters and injects them into
`GameEngine` through the ports of `game/ports.py`; `GameEngine` still builds the
client JSON.

## Decisions

Architecture decisions are recorded in [`docs/adr/`](adr/), one file per decision
(`NNNN-title.md`: context, decision, consequences). The `grill-with-docs` skill
writes them.

## Known debt

Tracked on GitHub; the rules in `.claude/rules/` describe the target, these items do
not meet it yet.

- `server.py` (~570 lines) exceeds the ~500-line budget (#5).
- Routes do not validate their bodies, no upload size limit, CORS open to any origin
  (#2).
- `api/interpreter.py` parses the LLM output from prose instead of constraining it with
  a schema (#3).
- Coverage is ~54%, weak on NPC planning and adapters (#4).
- About 40 unused functions, attributes and constants that vulture reports at 60%
  confidence; the gate runs at 80% until they are removed (#8).
- `static/renderer.js` (~950 lines) exceeds the ~500-line budget.
