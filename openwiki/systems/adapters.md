---
type: system
title: Adapters, Voxtral, ElevenLabs and logging
description: The api/ package that implements the domain ports with Mistral Voxtral, ElevenLabs plus the pygame mixer, and a JSONL pipeline logger, plus the NPC roster that feeds both.
tags: [adapters, voxtral, elevenlabs, logging, ports]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-18T09:41:00.050Z
sources:
  - id: openwiki-source-6e21f962de7f225422324196
    resource: repo://api/constants.py
  - id: openwiki-source-5a30db6dbee6aab6793cc16a
    resource: repo://api/interpreter.py
  - id: openwiki-source-b7fcb6ba7b5ef12e584d14ba
    resource: repo://api/logger.py
  - id: openwiki-source-e9c3e06b2d604594c651cc11
    resource: repo://api/roster.py
  - id: openwiki-source-18da8bfe4ae2cbf4ece58cf2
    resource: repo://api/tts.py
generated: { by: "claude-code", at: "2026-11-18T09:30:24.405Z" }
---

# Adapters: Voxtral, ElevenLabs, logging

`api/` holds one module per external system. An adapter implements a port from `game/ports.py`, holds no game rule and turns vendor failures into the port's error. See [System overview](../architecture/system-overview.md).

## Voxtral order interpreter (`api/interpreter.py`)

`VoxtralOrderInterpreter` implements `OrderInterpreter` with one multimodal chat call per command, with no separate transcription step.

- **Model and tool.** The model is `voxtral-small-latest` and the forced function is `give_npc_orders` (both in `api/constants.py`). The call passes the audio as `input_audio` plus a short text instruction, with the system prompt built from the roster.
- **Forced tool call.** The request sets `tool_choice="any"`. The tool's JSON schema requires `orders[]` items with `npc_id` (integer), `action` (enum built from `ActionType`) and `voice_line`, and sets `additionalProperties: false`. The answer is never parsed as prose.
- **Validation.** `read_orders_answer` finds the `give_npc_orders` call and checks each item. A missing call gives `CommandRefused(NO_ORDERS_GIVEN)`. A bad shape gives `MALFORMED_ANSWER`, an unknown action `UNKNOWN_ACTION`, an unknown NPC id `UNKNOWN_NPC`. One bad item refuses the whole command.
- **Failure translation.** `interpret` re-raises `OrderInterpretationError` and wraps any other exception in one whose message names only the failure type. The type and text go to the log, never the secret.
- **Client and roster.** The Mistral client is created lazily from `MISTRAL_API_KEY` unless one is injected. `register_roster(npcs)` stores id, name, kind and allowed actions per NPC; the prompt lists them in a table with each NPC's personality, and answers are matched against that roster.

The system prompt tells the model to still give an order when the NPC cannot do the action, with an in-character refusal as voice line. The NPC then refuses it at enqueue time. See [Voice order flow](../workflows/voice-order-flow.md).

## ElevenLabs speaker (`api/tts.py`)

`TTSEngine` implements `VoiceLineSpeaker`.

- Constructor arguments `create_client` and `play_audio` are injectable. Tests pass a fake client factory and a fake playback (`tests/test_tts.py`); the defaults build a real `ElevenLabs` client and play through `pygame.mixer`.
- Without `ELEVENLABS_API_KEY`, or if client creation raises, `_client` is `None`: no thread starts and `speak` returns without doing anything.
- `speak` enqueues `(voice_line, npc_name)`, ignoring blank lines. A daemon worker thread takes lines in FIFO order, looks up the voice by NPC name (`NPC_VOICE_MAP`, fallback Rachel), calls `text_to_speech.with_raw_response.convert` with model `eleven_turbo_v2_5` and `mp3_22050_32`, reads `character-cost` and `tts-latency-ms` headers, logs, then plays the clip, blocking until it ends.
- Any exception in the worker is logged and the worker continues. `close()` stops it with a sentinel.

## Roster (`api/roster.py`)

`NPC_PROFILES` is the single registry of NPC identities: a name from `NPCName`, a personality text ("soul") and an `ElevenLabsVoice`. `CHARACTER_SOULS` and `NPC_VOICE_MAP` are derived from it. `get_soul` falls back to a neutral personality for unknown names. The prompt builder and the TTS voice lookup both read these maps.

## Pipeline logger (`api/logger.py`)

`pipeline_logger` is a module-level `PipelineLogger` that configures loguru at import: a stderr sink, a `.log` file and a `.jsonl` file under `logs/`. It records LLM start and end, TTS start and end, and a session summary. It estimates cost from token counts and per-character prices defined in the module, keeps running totals, and is closed by `GameEngine.stop()`. Logs hold transcripts, orders and costs, never audio or keys.

## Related pages

- [Running and configuration](../operations/running-and-configuration.md)
- [Testing and quality gates](../testing/quality-gates-and-tests.md)
