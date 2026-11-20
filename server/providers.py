"""Picks the LLM provider from the environment and builds its order interpreters.

Adding a provider: a ``LlmProvider`` member and its key variable in
``server/constants.py``, an adapter module in ``api/``, and one ``case`` in
``build_order_interpreters`` (`docs/architecture.md` § Adding an LLM provider).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from api.interpreter import MistralOrderInterpreter
from api.logger import PipelineLogger
from game.npc import NPC
from game.ports import TextOrderInterpreter, VoiceOrderInterpreter
from server.constants import (
    API_KEY_VARIABLES,
    DEFAULT_LLM_PROVIDER,
    LLM_PROVIDER_VARIABLE,
    LlmProvider,
)


@dataclass(frozen=True)
class ProviderChoice:
    provider: LlmProvider
    api_key: str


@dataclass(frozen=True)
class OrderInterpreters:
    """The adapters of one provider. ``voice`` is ``None`` when the provider has no
    speech input: the game then takes typed commands only."""

    text: TextOrderInterpreter
    voice: VoiceOrderInterpreter | None
    register_roster: Callable[[Sequence[NPC]], None]


def read_provider_choice(environment: Mapping[str, str]) -> ProviderChoice:
    """The provider named by ``G4AL_LLM_PROVIDER`` (default ``mistral``) and its key.

    Raises ``SystemExit`` with a message naming the variable at fault when the provider
    is unknown or its key variable is unset or empty.
    """
    name = environment.get(LLM_PROVIDER_VARIABLE, "").strip().lower() or DEFAULT_LLM_PROVIDER
    try:
        provider = LlmProvider(name)
    except ValueError:
        known = ", ".join(LlmProvider)
        message = f"{LLM_PROVIDER_VARIABLE}={name!r} is not a known provider (one of: {known})"
        raise SystemExit(message) from None
    key_variable = API_KEY_VARIABLES[provider]
    api_key = environment.get(key_variable, "").strip()
    if not api_key:
        raise SystemExit(f"{key_variable} is not set: the {provider} provider needs it")
    return ProviderChoice(provider=provider, api_key=api_key)


def build_order_interpreters(
    choice: ProviderChoice, *, pipeline_logger: PipelineLogger
) -> OrderInterpreters:
    match choice.provider:
        case LlmProvider.MISTRAL:
            interpreter = MistralOrderInterpreter.from_api_key(
                choice.api_key, pipeline_logger=pipeline_logger
            )
            return OrderInterpreters(
                text=interpreter, voice=interpreter, register_roster=interpreter.register_roster
            )
