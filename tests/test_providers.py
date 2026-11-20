import pytest

from api.logger import PipelineLogger
from api.model_catalog import MODEL_CATALOG, MODELS_BY_ID, LlmProvider
from server.app import build_engine
from server.constants import API_KEY_VARIABLES
from server.providers import build_order_interpreters, read_startup_models
from tests.fakes import RecordingSpeaker


@pytest.mark.parametrize(
    ("environment", "model_id"),
    [
        ({"MISTRAL_API_KEY": "key"}, "voxtral-small-latest"),
        ({"G4AL_LLM_PROVIDER": " Mistral ", "MISTRAL_API_KEY": "key"}, "voxtral-small-latest"),
        ({"G4AL_LLM_MODEL": "", "MISTRAL_API_KEY": "key"}, "voxtral-small-latest"),
        (
            {"G4AL_LLM_MODEL": " mistral-large-latest ", "MISTRAL_API_KEY": "key"},
            "mistral-large-latest",
        ),
    ],
    ids=["defaults", "provider-spaced-capitalised", "model-empty", "model-named"],
)
def test_the_game_starts_on_the_named_model_or_the_provider_default(
    environment: dict[str, str], model_id: str
) -> None:
    startup = read_startup_models(environment)

    assert startup.selected is MODELS_BY_ID[model_id]
    assert startup.available_models == MODEL_CATALOG
    assert startup.api_keys == {LlmProvider.MISTRAL: "key"}


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({}, "MISTRAL_API_KEY is not set: the mistral provider needs it"),
        ({"MISTRAL_API_KEY": "  "}, "MISTRAL_API_KEY is not set: the mistral provider needs it"),
        (
            {"G4AL_LLM_PROVIDER": "acme", "MISTRAL_API_KEY": "key"},
            "G4AL_LLM_PROVIDER='acme' is not a known provider (one of: mistral)",
        ),
        (
            {"G4AL_LLM_MODEL": "gpt-unknown", "MISTRAL_API_KEY": "key"},
            f"G4AL_LLM_MODEL='gpt-unknown' is not a known model (one of: {', '.join(MODELS_BY_ID)})",
        ),
    ],
    ids=["key-missing", "key-blank", "unknown-provider", "unknown-model"],
)
def test_startup_exits_naming_the_variable_at_fault(
    environment: dict[str, str], message: str
) -> None:
    with pytest.raises(SystemExit) as raised:
        read_startup_models(environment)

    assert str(raised.value) == message


@pytest.mark.parametrize("provider", list(LlmProvider))
def test_every_provider_has_a_key_variable_and_a_text_interpreter(provider: LlmProvider) -> None:
    interpreters = build_order_interpreters(
        provider, api_key="key", pipeline_logger=PipelineLogger()
    )

    assert API_KEY_VARIABLES[provider]
    assert callable(interpreters.text.interpret_text)


def test_the_built_engine_starts_on_the_start_model_among_the_available_ones() -> None:
    startup = read_startup_models(
        {"G4AL_LLM_MODEL": "mistral-small-latest", "MISTRAL_API_KEY": "key"}
    )

    engine = build_engine(startup, speaker=RecordingSpeaker(), pipeline_logger=PipelineLogger())

    state = engine.get_state()
    assert state["selectedModelId"] == "mistral-small-latest"
    assert [model["id"] for model in state["models"]] == list(MODELS_BY_ID)
    assert state["hasVoiceInput"] is False
