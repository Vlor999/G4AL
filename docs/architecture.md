# Architecture

## Runtime

```
Browser (static/: Canvas renderer, input, push-to-talk)
   │  HTTP: /api/state, /api/action, /api/select, /api/move,
   │        /api/discard, /api/dismiss_storage, /api/audio
   │  Socket.IO: state push (~60 FPS)
   ▼
server.py: Flask + Socket.IO, GameEngine (game loop thread)
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

- `api/interpreter.py` parses the LLM output from prose (fence stripping) instead of
  constraining it with a schema (`.claude/rules/structured-llm-output.md`).
- `game/npc.py` and `static/renderer.js` exceed the ~500-line budget.
