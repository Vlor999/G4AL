import pytest

from tests.fakes import TEXT_MODEL, VOICE_MODEL, ScriptedOrderInterpreter, build_model_selection


def test_a_selection_must_start_on_an_available_model() -> None:
    interpreter = ScriptedOrderInterpreter()

    with pytest.raises(ValueError, match="mistral-small-latest is not an available model"):
        build_model_selection(interpreter, selected=TEXT_MODEL, available_models=[VOICE_MODEL])
