---
type: system
title: LLM models and providers
description: Which LLM models can interpret orders, how the start model and the available models come from the environment, how the player switches model in game, what a text-only model changes, and how to add a provider.
tags: [llm, models, providers, configuration, mistral]
verified:
  - by: openwiki/0.5.2
    at: 2026-11-28T10:49:24.445Z
sources:
  - id: openwiki-source-4a7abb12a40e98905af9e3a5
    resource: repo://api/model_catalog.py
  - id: openwiki-source-0d5ad3511dcf5d6f5ad53c00
    resource: repo://server/engine.py
  - id: openwiki-source-b4711c804efbd2e1bf190ccf
    resource: repo://server/model_selection.py
  - id: openwiki-source-fbf7171f46d33a488a6bdda0
    resource: repo://server/providers.py
  - id: openwiki-source-ad8a0f8b85e961c2b13636c0
    resource: repo://server/serialization.py
generated: { by: "claude-code", at: "2026-11-28T10:49:24.445Z" }
---

# LLM models and providers

Every command, typed or spoken, goes to one LLM model. Which one is entry point state, not a game rule: the model that interprets an order does not change what the order does. The adapters themselves are on [Adapters](adapters.md); the command path is on [Voice and typed order flow](../workflows/voice-order-flow.md).

## Model catalog (`api/model_catalog.py`)

`MODEL_CATALOG` lists the models the player can pick. Each `CatalogModel` has a provider (`LlmProvider`), the id the vendor API takes, a display name, whether it hears audio (`has_voice_input`), and its prices in USD per input token, per output token and per second of input audio. `MODELS_BY_ID` indexes them; the pipeline logger prices every call from it.

| Id | Name | Voice input |
|---|---|---|
| `voxtral-small-latest` | Voxtral Small | yes |
| `mistral-small-latest` | Mistral Small 4 | no |
| `mistral-large-latest` | Mistral Large 4 | no |
| `ministral-14b-latest` | Ministral 3 14B | no |
| `ministral-8b-latest` | Ministral 3 8B | no |
| `ministral-3b-latest` | Ministral 3 3B | no |
| `codestral-latest` | Codestral | no |

Mistral is the only provider today. Its default model (`DEFAULT_MODELS`) is Voxtral Small, the one that keeps push-to-talk. The module records the vendor pages its ids and prices were read from, and a residual risk on the Voxtral alias to recheck if voice commands start failing.

## Start model and available models (`server/providers.py`)

`read_startup_models(environment)` runs in `main()` before any side effect and returns a `StartupModels`:

- **Start model.** The model `G4AL_LLM_MODEL` names, or else the default model of `G4AL_LLM_PROVIDER` (default `mistral`).
- **API keys.** One per provider whose key variable (`API_KEY_VARIABLES`, `MISTRAL_API_KEY` for Mistral) is set and not blank.
- **Available models.** Every catalog model whose provider has a key, in catalog order.

It raises `SystemExit` with a message naming the variable at fault when the provider or the model is unknown, or when the start model's provider has no key. So the server never starts unable to interpret a command. See [Running and configuration](../operations/running-and-configuration.md).

`build_order_interpreters(provider, *, api_key, pipeline_logger)` builds one provider's `OrderInterpreters`: a text interpreter, a voice interpreter or `None` for a provider without speech input, and a `register_roster` callback. For Mistral, one `MistralOrderInterpreter` fills both roles. `build_engine` in `server/app.py` calls it for every provider with a key and registers the NPC roster with each.

## Switching model in game (`server/model_selection.py`)

`ModelSelection` holds the available models, the interpreters per provider and the selected model, behind its own lock, so any thread may use it. Its constructor raises `ValueError` when the start model is not available.

- `select(model_id)` makes that model the one of the next commands and returns `False`, changing nothing, for an id outside the available models. `POST /api/model` calls it through `GameEngine.select_model`; a command already sent keeps its model.
- `selected()` returns a `SelectedModel`: the model, its provider's text interpreter, and the voice interpreter only when the model has voice input.

When the selected model does not hear audio, `voice` is `None`. Then:

- `GameEngine.send_audio_command` returns `False` and `/api/audio` answers 400.
- The state sends `hasVoiceInput: false`, so the client neither starts push-to-talk nor shows the microphone hint.
- Typed commands still work.

The state also sends `models` (id, name, voice input) and `selectedModelId` for the picker. See [Browser client](browser-client.md).

## Adding a provider

`docs/architecture.md` § Adding an LLM provider gives the steps:

1. Write an adapter in `api/` that implements `TextOrderInterpreter`, and `VoiceOrderInterpreter` only if the provider takes audio. It sends the shared prompt and schema of `api/order_contract.py`, hands the answer to `parse_orders`, and translates vendor errors into `OrderInterpretationError`.
2. Add an `LlmProvider` member, its key variable to `API_KEY_VARIABLES` and to `.env.example`.
3. List its models and prices in `MODEL_CATALOG` and its default in `DEFAULT_MODELS`.
4. Add one `case` to `build_order_interpreters`.

## Tests

`tests/test_model_catalog.py`, `tests/test_providers.py` and `tests/test_model_selection.py` cover the catalog, the environment rules and the selection. `tests/fakes.py` provides `build_model_selection`, which wires a `ScriptedOrderInterpreter` as the Mistral provider with or without a voice adapter. See [Testing and quality gates](../testing/quality-gates-and-tests.md).
