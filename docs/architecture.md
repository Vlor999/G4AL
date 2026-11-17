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
3. The answer is parsed into a `CommandResponse` (one `NPCOrder` per NPC). The game
   loop picks it up on its next tick (`_apply_pending_response`) and enqueues the
   actions on each NPC.
4. Each NPC's reply goes to `api.tts`, which plays it in the background.

## Layers

See [`.claude/rules/architecture.md`](../.claude/rules/architecture.md). Today
`GameEngine` in `server.py` still holds some game decisions (spawning, response
application, serialization). They move to `game/` as PRs touch them.

## Decisions

Architecture decisions are recorded in [`docs/adr/`](adr/), one file per decision
(`NNNN-title.md`: context, decision, consequences). The `grill-with-docs` skill
writes them.

## Known debt

Tracked on GitHub; the rules in `.claude/rules/` describe the target, these items do
not meet it yet.

- Game rules and technical code are mixed: `GameEngine` in `server.py` holds game
  decisions and routes mutate NPCs under `engine._lock`. `game/npc.py` (~1150 lines)
  and `server.py` (~690 lines) exceed the ~500-line budget (#5).
- Routes do not validate their bodies, no upload size limit, CORS open to any origin
  (#2).
- `api/interpreter.py` parses the LLM output from prose instead of constraining it with
  a schema (#3).
- Coverage is ~54%, weak on NPC planning and adapters (#4).
- About 40 unused functions, attributes and constants that vulture reports at 60%
  confidence; the gate runs at 80% until they are removed (#8).
- `static/renderer.js` (~950 lines) exceeds the ~500-line budget.
