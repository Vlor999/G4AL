"""The pipeline sinks of api/logger.py."""

from pathlib import Path

import pytest
from loguru import logger

from api.logger import configure_sinks


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
