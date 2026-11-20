import pytest

from api.logger import PipelineLogger
from server.constants import API_KEY_VARIABLES, LlmProvider
from server.providers import ProviderChoice, build_order_interpreters, read_provider_choice


@pytest.mark.parametrize(
    "environment",
    [
        {"MISTRAL_API_KEY": "key"},
        {"G4AL_LLM_PROVIDER": "", "MISTRAL_API_KEY": "key"},
        {"G4AL_LLM_PROVIDER": " Mistral ", "MISTRAL_API_KEY": "key"},
    ],
    ids=["unset", "empty", "spaced-capitalised"],
)
def test_the_provider_defaults_to_mistral_and_reads_its_key(environment: dict[str, str]) -> None:
    assert read_provider_choice(environment) == ProviderChoice(LlmProvider.MISTRAL, "key")


@pytest.mark.parametrize(
    ("environment", "message"),
    [
        ({}, "MISTRAL_API_KEY is not set: the mistral provider needs it"),
        ({"MISTRAL_API_KEY": "  "}, "MISTRAL_API_KEY is not set: the mistral provider needs it"),
        (
            {"G4AL_LLM_PROVIDER": "acme", "MISTRAL_API_KEY": "key"},
            "G4AL_LLM_PROVIDER='acme' is not a known provider (one of: mistral)",
        ),
    ],
    ids=["key-missing", "key-blank", "unknown-provider"],
)
def test_startup_exits_naming_the_variable_at_fault(
    environment: dict[str, str], message: str
) -> None:
    with pytest.raises(SystemExit) as raised:
        read_provider_choice(environment)

    assert str(raised.value) == message


@pytest.mark.parametrize("provider", list(LlmProvider))
def test_every_provider_has_a_key_variable_and_a_text_interpreter(provider: LlmProvider) -> None:
    interpreters = build_order_interpreters(
        ProviderChoice(provider, "key"), pipeline_logger=PipelineLogger()
    )

    assert API_KEY_VARIABLES[provider]
    assert callable(interpreters.text.interpret_text)
