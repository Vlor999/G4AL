---
type: workflow
title: Voice and typed order flow
description: The path of a spoken or typed command from the browser to an NPC action and a spoken reply, including every point where the command can be refused or dropped.
tags: [voice, orders, llm, tts, chat, workflow]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-25T15:38:15.273Z
sources:
  - id: openwiki-source-bd1c9ad72f7e472b6efd8fe4
    resource: repo://api/order_contract.py
  - id: openwiki-source-89e94a5f3c0caa39f467f254
    resource: repo://game/orders/orders.py
  - id: openwiki-source-0d5ad3511dcf5d6f5ad53c00
    resource: repo://server/engine.py
  - id: openwiki-source-f7ec59fd0107dc945740979a
    resource: repo://server/routes.py
generated: { by: "claude-code", at: "2026-11-25T15:38:15.273Z" }
---

# Voice and typed order flow

A command crosses all four layers, whether the player speaks it (push-to-talk) or types it (chat panel). Each hand-off is a typed value, so a failure stops at the layer that detected it. Both inputs share every step after the route.

## Steps

1. **Send.**
   - Voice: the player holds `G`, which works only when the selected model hears audio. `static/ptt.js` records, converts to a 16 kHz mono WAV and posts it as multipart field `audio` to `/api/audio`.
   - Typed: `static/chat.js` posts `{text}` to `/api/command`.

   See [Browser client](../systems/browser-client.md).
2. **Accept.**
   - `/api/audio` reads the multipart file, or JSON `audio_b64`, and answers 400 if fewer than 100 bytes arrived. `GameEngine.send_audio_command` also refuses, and the route answers 400, when the selected model has no voice interpreter.
   - `/api/command` answers 400 for an empty or over-long text.

   See [HTTP and Socket.IO contract](../systems/http-and-socketio-contract.md).
3. **Start.** The engine binds the currently selected model and its interpreter, so a later model switch does not affect this command. Under the lock it logs "Interpreting the command..." and adds the command to the chat: `TypedCommand(text)` or `SpokenCommand()`. It then runs the interpretation through `run_in_background`, a daemon thread in production, and the HTTP request returns `{"ok": true}` at once. See [LLM models and providers](../systems/llm-models-and-providers.md).
4. **Interpret.** The worker calls `interpret_text(command, model_id=...)` or `interpret_voice(wav_bytes, model_id=...)`, which can block for seconds. `MistralOrderInterpreter` makes one chat call that forces the `give_npc_orders` function, then validates the arguments against the roster. See [Adapters](../systems/adapters.md).
5. **Hand over.** The worker appends the answer, or an `_InterpretationFailed` marker when the service failed, to `_pending_answers` under the engine lock. Answers queue up; none overwrites another.
6. **Apply.** On its next tick the game loop applies every pending answer in arrival order. For a list of orders it calls `apply_orders` on the NPC list. See [Game loop and state push](game-loop-and-state-push.md).
7. **Reply.** For each outcome:
   - if the order is marked spoken, the engine passes the voice line to the `VoiceLineSpeaker`;
   - for every outcome, accepted or not, it adds `Name: "line"` to the game log and an `NpcVoiceLine` to the chat;
   - when the order was accepted, the NPC shows the line in a speech bubble for 360 frames.

## Outcomes

| Situation | Where decided | Result |
|---|---|---|
| Service fails (network, API, any vendor error) | adapter raises `OrderInterpretationError` | Logged as an `order_interpretation` warning on the server; the game log says "Command failed, try again." without the service's error text |
| Selected model has no voice input | `GameEngine.send_audio_command` | `/api/audio` answers 400; nothing is logged or queued |
| Answer breaks the contract | adapter returns `CommandRefused(reason)` | Game log shows `Order refused: <reason>`; no order of that command is applied |
| Answer asks for `move_to` | adapter returns `CommandRefused(ACTION_NEEDS_TARGET)` | Refused as a whole: a spoken or typed order carries no target tile, so moving is a right-click |
| No orders found | adapter returns an empty list | Game log shows "No actions understood." |
| Order for an unknown NPC id | `apply_orders` | Not accepted: nothing enqueued, nothing spoken; its voice line still goes to the game log and chat |
| Action not allowed for that NPC | `NPC.enqueue` | NPC says "I can't do that!"; order not accepted, not spoken; its voice line still goes to the game log and chat |
| Accepted order | `apply_orders` | Action enqueued; a voice line is spoken for at most one order per command (`TTS_MAX_SPEAKERS = 1`); every line goes to the game log and chat |

The `RefusalReason` values are `no orders given`, `malformed answer`, `unknown action`, `unknown npc` and `action needs a target tile`. Several `give_npc_orders` calls in one answer are merged in call order, although the request asks for one (`parallel_tool_calls=False`).

## Why this shape

- The model is constrained by a tool schema, not parsed from prose, so an unexpected answer is a typed refusal rather than a crash.
- Order application happens on the game loop thread, never on the worker, so the simulation stays single-writer. See [System overview](../architecture/system-overview.md).
- The domain depends only on the ports, so the whole flow is tested with fakes (`ScriptedOrderInterpreter`, `RecordingSpeaker`, `run_now`) in `tests/e2e/test_command_orders.py`. See [Testing and quality gates](../testing/quality-gates-and-tests.md).
- Spoken replies run in `TTSEngine`'s own queue and never block the loop. Without an ElevenLabs key they are dropped.
