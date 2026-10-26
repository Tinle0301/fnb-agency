from __future__ import annotations

import json
import logging

import pytest

from app.logging_setup import JsonFormatter
from evals import fixtures as fx


class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setFormatter(JsonFormatter())
        self.lines: list[dict] = []

    def emit(self, record):
        self.lines.append(json.loads(self.format(record)))


@pytest.mark.asyncio
async def test_agent_logs_are_json_tagged_with_run_and_agent(orchestrator):
    handler = Capture()
    root = logging.getLogger()
    root.addHandler(handler)
    old_level = root.level
    root.setLevel(logging.INFO)
    try:
        run = await orchestrator.start_run(fx.BREWERY_BRIEF)
        await orchestrator.advance(run.id)
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
    lines = handler.lines
    completed = [l for l in lines if l["event"] == "agent.completed"]
    assert completed, lines
    entry = completed[0]
    assert entry["run_id"] == run.id
    assert entry["agent"] == "research_analyst"
    assert entry["stage"] == "research"
    assert entry["input_tokens"] == 100 and "latency_ms" in entry
