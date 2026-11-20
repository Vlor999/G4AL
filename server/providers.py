"""Reads the startup model and the available ones from the environment, and builds
each provider's order interpreters.

Adding a provider: a ``LlmProvider`` member and its key variable in
``server/constants.py``, its models in ``api/model_catalog.py``, an adapter module in
``api/``, and one ``case`` in ``build_order_interpreters`` (`docs/architecture.md`
§ Adding an LLM provider).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from api.interpreter import MistralOrderInterpreter
from api.logger import PipelineLogger
from api.model_catalog import (
    DEFAULT_MODELS,
    MODEL_CATALOG,
    MODELS_BY_ID,
    CatalogModel,
    LlmProvider,
)
from server.constants import (
    API_KEY_VARIABLES,
    DEFAULT_LLM_PROVIDER,
    LLM_MODEL_VARIABLE,
    LLM_PROVIDER_VARIABLE,
)
from server.model_selection import OrderInterpreters


@dataclass(frozen=True)
class StartupModels:
    """The model the game starts on, the models the player may pick (those whose
    provider key is set), and the API key of each of their providers."""

    selected: CatalogModel
    available_models: tuple[CatalogModel, ...]
    api_keys: dict[LlmProvider, str]


def read_startup_models(environment: Mapping[str, str]) -> StartupModels:
    """The model ``G4AL_LLM_MODEL`` names, or else the default model of
    ``G4AL_LLM_PROVIDER`` (default ``mistral``), and the models the player may pick.

    Raises ``SystemExit`` with a message naming the variable at fault when the provider
    or the model is unknown, or when the key of the start model's provider is unset or
    empty.
    """
    provider = _read_provider(environment)
    selected = _read_model(environment) or DEFAULT_MODELS[provider]
    api_keys = {
        key_provider: key
        for key_provider, variable in API_KEY_VARIABLES.items()
        if (key := environment.get(variable, "").strip())
    }
    if selected.provider not in api_keys:
        variable = API_KEY_VARIABLES[selected.provider]
        raise SystemExit(f"{variable} is not set: the {selected.provider} provider needs it")
    available = tuple(model for model in MODEL_CATALOG if model.provider in api_keys)
    return StartupModels(selected=selected, available_models=available, api_keys=api_keys)


def _read_provider(environment: Mapping[str, str]) -> LlmProvider:
    name = environment.get(LLM_PROVIDER_VARIABLE, "").strip().lower() or DEFAULT_LLM_PROVIDER
    try:
        return LlmProvider(name)
    except ValueError:
        known = ", ".join(LlmProvider)
        message = f"{LLM_PROVIDER_VARIABLE}={name!r} is not a known provider (one of: {known})"
        raise SystemExit(message) from None


def _read_model(environment: Mapping[str, str]) -> CatalogModel | None:
    model_id = environment.get(LLM_MODEL_VARIABLE, "").strip()
    if not model_id:
        return None
    model = MODELS_BY_ID.get(model_id)
    if model is None:
        known = ", ".join(MODELS_BY_ID)
        raise SystemExit(
            f"{LLM_MODEL_VARIABLE}={model_id!r} is not a known model (one of: {known})"
        )
    return model


def build_order_interpreters(
    provider: LlmProvider, *, api_key: str, pipeline_logger: PipelineLogger
) -> OrderInterpreters:
    match provider:
        case LlmProvider.MISTRAL:
            interpreter = MistralOrderInterpreter.from_api_key(
                api_key, pipeline_logger=pipeline_logger
            )
            return OrderInterpreters(
                text=interpreter, voice=interpreter, register_roster=interpreter.register_roster
            )
