"""The LLM models the player can pick, with their prices.

One entry per model: its provider, the id the vendor API takes, the name the picker
shows, whether it hears audio (push-to-talk), and its prices in USD. Mistral keeps the
models its function calling guide lists that are current on its model overview: the
interpreter forces a tool call (``tool_choice="any"``) on every command.

Sources, read 2026-11-20:
- https://docs.mistral.ai/capabilities/function_calling/ (models with function calling)
- https://docs.mistral.ai/getting-started/models/models_overview/ (current models)
- the model cards linked from the overview, for the prices. Only the Mistral Large 4
  card labels them ("Input", "Output"); the others list two token prices in the same
  order, read here as input then output.
- https://mistral.ai/pricing ("$0.5 /M tokens in and $1.5 /M tokens out" for Mistral
  Large, which disagrees with the Large 4 card; the card is used).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

_PER_MILLION = 1 / 1_000_000


class LlmProvider(StrEnum):
    """The LLM providers the entry point can build order interpreters for."""

    MISTRAL = "mistral"


@dataclass(frozen=True)
class ModelPrices:
    """USD per input token, per output token, and per second of input audio."""

    input_per_token: float
    output_per_token: float
    audio_per_second: float = 0.0


@dataclass(frozen=True)
class CatalogModel:
    provider: LlmProvider
    model_id: str
    display_name: str
    has_voice_input: bool
    prices: ModelPrices


def _mistral_text_model(
    model_id: str, display_name: str, *, input_price: float, output_price: float
) -> CatalogModel:
    prices = ModelPrices(input_price * _PER_MILLION, output_price * _PER_MILLION)
    return CatalogModel(LlmProvider.MISTRAL, model_id, display_name, False, prices)


# Checked 2026-11-20: https://docs.mistral.ai/models/voxtral-small-25-07 lists the API names
# `voxtral-small-2507` and `voxtral-small-latest`, status GA, input audio and text, features
# chat-completions and function-calling, and no deprecation date
# (https://docs.mistral.ai/models lists Voxtral Small among the current models).
# https://docs.mistral.ai/studio/audio/audio-in-chat uses `voxtral-small-latest` with a tool
# and `tool_choice` "any". Voxtral 3 (`voxtral-small-transcribe-latest`) is a transcription
# model and does not replace it for chat with tool calls.
# Residual risk: https://docs.mistral.ai/studio/audio/migrate-from-voxtral-2 maps the dated ID
# behind the alias, `voxtral-small-2507`, to `voxtral-small-transcribe-latest`, which only
# serves `/v1/audio/transcriptions`, and its deprecation timeline is empty as of 2026-11-20.
# Recheck that page if voice commands start failing.
VOXTRAL_SMALL = CatalogModel(
    LlmProvider.MISTRAL,
    "voxtral-small-latest",
    "Voxtral Small",
    True,
    # https://docs.mistral.ai/models/voxtral-small-25-07: $0.1 and $0.4 / M tokens,
    # $0.004 / min of audio, reported apart from the tokens (`prompt_audio_seconds`).
    ModelPrices(0.1 * _PER_MILLION, 0.4 * _PER_MILLION, audio_per_second=0.004 / 60),
)

MODEL_CATALOG: tuple[CatalogModel, ...] = (
    VOXTRAL_SMALL,
    # https://docs.mistral.ai/models/mistral-small-4-0-26-03
    _mistral_text_model(
        "mistral-small-latest", "Mistral Small 4", input_price=0.15, output_price=0.6
    ),
    # https://docs.mistral.ai/models/mistral-large-4-0
    _mistral_text_model(
        "mistral-large-latest", "Mistral Large 4", input_price=0.7, output_price=2.1
    ),
    # https://docs.mistral.ai/models/ministral-3-14b-25-12
    _mistral_text_model(
        "ministral-14b-latest", "Ministral 3 14B", input_price=0.2, output_price=0.2
    ),
    # https://docs.mistral.ai/models/ministral-3-8b-25-12
    _mistral_text_model(
        "ministral-8b-latest", "Ministral 3 8B", input_price=0.15, output_price=0.15
    ),
    # https://docs.mistral.ai/models/ministral-3-3b-25-12
    _mistral_text_model("ministral-3b-latest", "Ministral 3 3B", input_price=0.1, output_price=0.1),
    # https://docs.mistral.ai/models/codestral-25-08
    _mistral_text_model("codestral-latest", "Codestral", input_price=0.3, output_price=0.9),
)

MODELS_BY_ID: dict[str, CatalogModel] = {model.model_id: model for model in MODEL_CATALOG}

# The model a provider starts on when G4AL_LLM_MODEL is not set. Voxtral for Mistral:
# it is the one that keeps push-to-talk.
DEFAULT_MODELS: dict[LlmProvider, CatalogModel] = {LlmProvider.MISTRAL: VOXTRAL_SMALL}
