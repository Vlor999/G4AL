---
type: workflow
title: Voice order flow
description: The path of a spoken command from the push-to-talk key to an NPC action and a spoken reply, including every point where the command can be refused or dropped.
tags: [voice, orders, voxtral, tts, workflow]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:41:00.050Z
sources:
  - id: openwiki-source-d31645d2375ae8305792ee37
    resource: repo://game/orders.py
  - id: openwiki-source-0d5ad3511dcf5d6f5ad53c00
    resource: repo://server/engine.py
  - id: openwiki-source-f7ec59fd0107dc945740979a
    resource: repo://server/routes.py
generated: { by: "claude-code", at: "2026-11-18T09:41:00.050Z" }
---

# Voice order flow

A voice command crosses all four layers. Each hand-off is a typed value, so a failure stops at the layer that detected it.

## Steps

1. **Record.** The player holds `G`. `static/ptt.js` records, converts to a 16 kHz mono WAV and posts it as multipart field `audio` to `/api/audio`. See [Browser client](../systems/browser-client.md).
2. **Accept.** The route reads the multipart file, or JSON `audio_b64`, and answers 400 if fewer than 100 bytes arrived. Otherwise it calls `GameEngine.send_audio_command`, which logs "Listening..." and starts a daemon worker thread, so the HTTP request returns `{"ok": true}` at once. See [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md).
3. **Interpret.** The worker calls `OrderInterpreter.interpret(wav_bytes)`, which can block for seconds. `VoxtralOrderInterpreter` makes one multimodal call that forces the `give_npc_orders` function, then validates the arguments. See [Adapters](../systems/adapters.md).
4. **Hand over.** The worker stores the result in `_pending_orders` under the engine lock. A newer command overwrites a pending one that was not applied yet.
5. **Apply.** On its next tick the game loop calls `_apply_pending_orders`, which runs `apply_orders` on the NPC list. See [Game loop and state push](game-loop-and-state-push.md).
6. **Reply.** For each outcome, if the order is marked spoken, the engine passes the voice line to the `VoiceLineSpeaker`; it then adds `Name: "line"` to the game log for every outcome, accepted or not. The NPC also shows the line in a speech bubble (360 frames) when its order was accepted.

## Outcomes

| Situation | Where decided | Result |
|---|---|---|
| Service fails (missing key, network, API) | adapter raises `OrderInterpretationError` | Logged as a warning by the engine; game unchanged. The game log keeps its "Listening..." line and gets no other |
| Answer breaks the contract | adapter returns `CommandRefused(reason)` | Log shows `Order refused: <reason>` after "Listening..."; no order of that command is applied |
| No orders heard | adapter returns an empty list | Log shows "No actions understood." |
| Order for an unknown NPC id | `apply_orders` | Not accepted: nothing enqueued, nothing spoken; its voice line is still added to the game log |
| Action not allowed for that NPC | `NPC.enqueue` | NPC says "I can't do that!"; order not accepted, not spoken; its voice line is still added to the game log |
| Accepted order | `apply_orders` | Action enqueued; a voice line is spoken for at most one order per command (`TTS_MAX_SPEAKERS = 1`); every accepted order's line goes to the game log |

The `RefusalReason` values are `no orders given`, `malformed answer`, `unknown action` and `unknown npc`.

## Why this shape

- The model is constrained by a tool schema, not parsed from prose, so an unexpected answer is a typed refusal rather than a crash.
- Order application happens on the game loop thread, never on the worker, so the simulation stays single-writer. See [System overview](../architecture/system-overview.md).
- The domain depends only on the two ports, so the whole flow is tested with fakes (`ScriptedOrderInterpreter`, `RecordingSpeaker`). See [Testing and quality gates](../testing/quality-gates-and-tests.md).
- Spoken replies run in `TTSEngine`'s own queue and never block the loop. Without an ElevenLabs key they are dropped silently.
