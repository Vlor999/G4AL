"""The pipeline sinks of api/logger.py and the log lines they keep."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from loguru import logger

from api.constants import AUDIO_MODEL
from api.logger import configure_sinks, has_event, pipeline_logger


@pytest.fixture
def llm_end_records() -> Iterator[list[tuple[str, dict[str, Any]]]]:
    """The message and ``extra`` fields of every ``llm_end`` record the sinks keep."""
    records: list[tuple[str, dict[str, Any]]] = []
    handler_id = logger.add(
        lambda message: records.append((message.record["message"], message.record["extra"])),
        filter=lambda record: has_event(record) and record["extra"]["event"] == "llm_end",
    )
    yield records
    logger.remove(handler_id)


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
    llm_end_records: list[tuple[str, dict[str, Any]]],
    orders: list[dict[str, Any]],
    described: str,
) -> None:
    pipeline_logger.llm_end(order={"orders": orders}, prompt_tokens=10, completion_tokens=5)

    [(message, _)] = llm_end_records
    assert message.startswith(f"LLM response: {described} | tokens=10+5 | ")


def test_a_failed_call_is_labelled_and_priced_as_the_audio_model(
    llm_end_records: list[tuple[str, dict[str, Any]]],
) -> None:
    pipeline_logger.llm_end(
        order=None, prompt_tokens=1_000_000, completion_tokens=1_000_000, error="timeout"
    )

    [(_, extra)] = llm_end_records
    assert (extra["model"], extra["cost_usd"]) == (AUDIO_MODEL, pytest.approx(0.1 + 0.4))
