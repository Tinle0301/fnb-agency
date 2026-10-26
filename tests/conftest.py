from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import pytest

from app.config import Settings
from app.llm import LLMResult
from app.memory.facts import InMemoryBrandMemory
from app.memory.session import InMemorySessionStore
from app.notify import Notifier
from app.orchestrator import Orchestrator
from evals import fixtures as fx


@dataclass
class Call:
    output_type: type
    model: str
    system: str
    prompt: str


@dataclass
class FakeLLM:
    """Returns golden fixtures by output type. Queue overrides with `script(type, *outputs)`."""

    defaults: dict = field(default_factory=lambda: dict(fx.BREWERY_OUTPUTS))
    queued: dict = field(default_factory=lambda: defaultdict(list))
    calls: list[Call] = field(default_factory=list)
    fail_on: type | None = None

    def script(self, output_type: type, *outputs) -> None:
        self.queued[output_type].extend(outputs)

    def prompts_for(self, output_type: type) -> list[str]:
        return [c.prompt for c in self.calls if c.output_type is output_type]

    async def generate(self, *, system, prompt, output_type, model, effort=None, max_tokens=16000):
        self.calls.append(Call(output_type, model, system, prompt))
        if self.fail_on is output_type:
            raise RuntimeError("simulated API outage")
        queue = self.queued[output_type]
        output = queue.pop(0) if queue else self.defaults[output_type]
        return LLMResult(output=output, model=model, input_tokens=100, output_tokens=50, stop_reason="end_turn")


@pytest.fixture
def settings() -> Settings:
    return Settings(storage="memory", max_qa_revisions=2)


@pytest.fixture
def llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def orchestrator(llm, settings) -> Orchestrator:
    return Orchestrator(llm, InMemorySessionStore(), InMemoryBrandMemory(), settings, Notifier())
