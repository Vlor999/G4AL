from api.model_catalog import DEFAULT_MODELS, MODEL_CATALOG, MODELS_BY_ID, LlmProvider


def test_every_model_id_is_listed_once() -> None:
    assert len(MODELS_BY_ID) == len(MODEL_CATALOG)


def test_every_provider_starts_on_one_of_its_own_models() -> None:
    assert set(DEFAULT_MODELS) == set(LlmProvider)
    for provider, model in DEFAULT_MODELS.items():
        assert model.provider is provider
        assert MODELS_BY_ID[model.model_id] is model


def test_only_voxtral_takes_voice_input_and_only_it_prices_audio() -> None:
    voice_models = [model.model_id for model in MODEL_CATALOG if model.has_voice_input]
    audio_priced = [model.model_id for model in MODEL_CATALOG if model.prices.audio_per_second]

    assert voice_models == audio_priced == ["voxtral-small-latest"]
