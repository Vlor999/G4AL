"""The pipeline sinks of api/logger.py and the log lines they keep."""

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from loguru import logger

from api.logger import PipelineLogger, configure_sinks
from tests.conftest import LlmEndRecords

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_VOXTRAL = "voxtral-small-latest"


def test_every_pipeline_sink_keeps_only_records_with_an_event(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    handler_ids = configure_sinks(tmp_path)
    logger.info("record without event")
    logger.bind(event="probe").info("record with event")
    for handler_id in handler_ids:
        logger.remove(handler_id)

    outputs = [capsys.readouterr().err] + [path.read_text() for path in sorted(tmp_path.iterdir())]
    assert len(outputs) == len(handler_ids)
    for output in outputs:
        assert "record with event" in output
        assert "record without event" not in output


@pytest.mark.parametrize(
    ("orders", "described"),
    [
        (
            [
                {"npc_id": 1, "npc_name": "Bob", "action": "chop_wood", "voice_line": "On it"},
                {"npc_id": 2, "npc_name": "Alice", "action": "mine_rock", "voice_line": "Sure"},
            ],
            "Bob→chop_wood, Alice→mine_rock",
        ),
        ([], "no orders"),
    ],
)
def test_the_llm_line_lists_each_order_of_the_answer(
    llm_end_records: LlmEndRecords,
    orders: list[dict[str, Any]],
    described: str,
) -> None:
    PipelineLogger().llm_end(
        order={"orders": orders}, prompt_tokens=10, completion_tokens=5, model=_VOXTRAL
    )

    [(message, _)] = llm_end_records
    assert message.startswith(f"LLM response: {described} | tokens=10+5 | ")


@pytest.mark.parametrize(
    ("model", "cost"),
    [
        ("voxtral-small-latest", 0.1 + 0.4),
        ("mistral-small-latest", 0.15 + 0.6),
        ("mistral-large-latest", 0.7 + 2.1),
    ],
)
@pytest.mark.parametrize("error", [None, "timeout"], ids=["answered", "failed"])
def test_a_call_is_labelled_and_priced_at_its_model_rates(
    llm_end_records: LlmEndRecords, model: str, cost: float, error: str | None
) -> None:
    PipelineLogger().llm_end(
        order=None,
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        model=model,
        error=error,
    )

    [(_, extra)] = llm_end_records
    assert (extra["model"], extra["cost_usd"]) == (model, pytest.approx(cost))


def test_the_audio_seconds_are_priced_per_minute_on_top_of_the_tokens(
    llm_end_records: LlmEndRecords,
) -> None:
    PipelineLogger().llm_end(
        order={"orders": []},
        prompt_tokens=1_000_000,
        completion_tokens=0,
        audio_seconds=90,
        model=_VOXTRAL,
    )

    [(message, extra)] = llm_end_records
    assert extra["audio_seconds"] == 90
    assert extra["audio_cost_usd"] == pytest.approx(0.006)
    assert extra["cost_usd"] == pytest.approx(0.1 + 0.006)
    assert "audio=90s" in message


def test_importing_the_logger_module_adds_no_sink_and_writes_no_line() -> None:
    probe = (
        "from loguru import logger\n"
        "logger.remove()\n"
        "records = []\n"
        "logger.add(records.append)\n"
        "import api.logger\n"
        "assert records == [], records\n"
        "logger.bind(event='probe').info('probe')\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed arguments, no outside input
        [sys.executable, "-c", probe], cwd=PROJECT_ROOT, capture_output=True, text=True
    )

    assert (result.returncode, result.stderr) == (0, "")
