---
type: system
title: Adapters, Mistral, ElevenLabs and logging
description: The api/ package that implements the domain ports with Mistral (typed and Voxtral audio commands), ElevenLabs plus the pygame mixer, and a JSONL pipeline logger, plus the provider-neutral order contract and the NPC roster.
tags: [adapters, mistral, voxtral, elevenlabs, logging, ports]
sources:
  - id: openwiki-source-6e21f962de7f225422324196
    resource: repo://api/constants.py
  - id: openwiki-source-5a30db6dbee6aab6793cc16a
    resource: repo://api/interpreter.py
  - id: openwiki-source-b7fcb6ba7b5ef12e584d14ba
    resource: repo://api/logger.py
  - id: openwiki-source-4601c7f853b2f0af6bd153c7
    resource: repo://api/npc_profiles.py
  - id: openwiki-source-bd1c9ad72f7e472b6efd8fe4
    resource: repo://api/order_contract.py
  - id: openwiki-source-18da8bfe4ae2cbf4ece58cf2
    resource: repo://api/tts.py
  - id: openwiki-source-141c86ea716204370c1b7a2d
    resource: repo://server/app.py
generated: { by: "claude-code", at: "2026-11-28T12:48:19.642Z" }
verified:
  - by: openwiki/0.5.2
    at: 2026-11-28T12:48:19.642Z
---

# Adapters: Mistral, ElevenLabs, logging

`api/` holds one module per external system. An adapter implements a port from `game/ports.py`, holds no game rule and turns vendor failures into the port's error. See [System overview](../architecture/system-overview.md). Which model a command goes to is chosen by the entry point; see [LLM models and providers](llm-models-and-providers.md).

## Order contract (`api/order_contract.py`)

The part every LLM provider shares, with no vendor SDK:

- **Roster.** `build_roster(npcs)` records id, name, kind and allowed actions per NPC, keeping only the actions an order without a target tile can give (`VOICE_ORDER_ACTIONS`, every `ActionType` except `move_to`).
- **System prompt.** `build_system_prompt(roster)` lists the roster as a table and each NPC's personality from `api/npc_profiles.py`. It tells the model to find every NPC and action pair, in the order given, and to still give an order the NPC cannot do, with an in-character refusal as voice line. The NPC then refuses it at enqueue time. See [Voice and typed order flow](../workflows/voice-order-flow.md).
- **Schema.** `ORDERS_SCHEMA` requires `orders[]` items with `npc_id` (integer), `action` (enum of `VOICE_ORDER_ACTIONS`) and `voice_line`, with `additionalProperties: false`. The answer is never parsed as prose.
- **Validation.** `parse_orders(arguments, roster)` accepts a JSON string or its decoded object. A bad shape gives `CommandRefused(MALFORMED_ANSWER)`, an action outside `ActionType` `UNKNOWN_ACTION`, `move_to` `ACTION_NEEDS_TARGET` (`action needs a target tile`), and an id outside the roster `UNKNOWN_NPC`. One bad item refuses the whole answer.

## Mistral interpreter (`api/interpreter.py`)

`MistralOrderInterpreter` implements both `TextOrderInterpreter` and `VoiceOrderInterpreter` with one chat call per command, to the catalog model the caller names.

- **Construction.** `from_api_key(api_key, *, pipeline_logger)` builds the Mistral client; the entry point calls it only when the key is set. Tests inject a client through the constructor.
- **Typed command.** `interpret_text(command, *, model_id)` sends the system prompt and `Give the orders of this typed command:` followed by the text.
- **Voice command.** `interpret_voice(audio, *, model_id)` sends the WAV as base64 `input_audio` plus a short text instruction to a voice model (Voxtral), with no separate transcription step.
- **Forced single tool call.** Both requests pass the `give_npc_orders` tool (`ORDERS_TOOL_NAME` in `api/constants.py`), `tool_choice="any"`, `parallel_tool_calls=False`, `temperature=0.7` and `max_tokens=1024`.
- **Reading the answer.** `read_orders_answer` takes every `give_npc_orders` call in the answer, in call order, and merges their orders; one refused call refuses the answer, and no call at all gives `CommandRefused(NO_ORDERS_GIVEN)`.
- **Failure translation.** `_interpret` catches any exception, logs its type and text under the `order_interpretation` event, and raises `OrderInterpretationError("Mistral could not interpret the command (<type>)")`. The error message never carries the vendor text or a secret.
- **Logging.** Each call logs `llm_start` with the typed text, or `(audio input)` for a recording. It then logs `llm_end` with token counts, the audio seconds Mistral reports (`prompt_audio_seconds`) and the model id, or with the refusal reason as error. A non-empty answer also logs a `pipeline_summary`.

## ElevenLabs speaker (`api/tts.py`)

`TTSEngine` implements `VoiceLineSpeaker`.

- Constructor arguments `pipeline_logger`, `create_client` and `play_audio` are keyword-only and injectable. Tests pass a fake client factory and a fake playback (`tests/test_tts.py`); the defaults build a real `ElevenLabs` client and play through `pygame.mixer`.
- Without `ELEVENLABS_API_KEY`, or if client creation raises, `_client` is `None`: a `tts_disabled` warning or error is logged, no thread starts and `speak` returns without doing anything.
- `speak` enqueues `(voice_line, npc_name)`, ignoring blank lines. A daemon worker thread takes lines in FIFO order, looks up the voice by NPC name (`NPC_VOICE_MAP`, fallback Rachel), calls `text_to_speech.with_raw_response.convert` with model `eleven_turbo_v2_5` and `mp3_22050_32`, reads the `character-cost` and `tts-latency-ms` headers, logs exactly one `tts_end`, then plays the clip, blocking until it ends.
- A synthesis failure is logged as `tts_end` with an error, a playback failure as `tts_playback`; in both cases the worker continues. `mask_api_key` replaces the key, as given and stripped, in every logged error text. `close()` stops the worker with a sentinel.

## NPC profiles (`api/npc_profiles.py`)

`NPC_PROFILES` is the single registry of NPC identities: a name from `NPCName`, a personality text ("soul") and an `ElevenLabsVoice`. `CHARACTER_SOULS` and `NPC_VOICE_MAP` are derived from it. `get_soul` falls back to a neutral personality for unknown names. The prompt builder and the TTS voice lookup both read these maps.

## Pipeline logger (`api/logger.py`)

`PipelineLogger` is built once by the entry point and handed to the adapters; importing the module adds no sink. `use_pipeline_sinks` installs the sinks (see [Running and configuration](../operations/running-and-configuration.md)).

- `llm_end` prices a call at the called model's catalog prices (`MODELS_BY_ID[model].prices`): input and output tokens plus input audio seconds, the audio part also logged apart as `audio_cost_usd`.
- `tts_end` prices the API-reported characters at `TTS_COST_PER_CHAR`.
- It keeps running totals, logs a `pipeline_summary` per answered command and a `session_end` summary on `close()`.

Logs hold transcripts of typed commands, orders and costs, never audio or keys.

## Related pages

- [LLM models and providers](llm-models-and-providers.md)
- [Testing and quality gates](../testing/quality-gates-and-tests.md)
