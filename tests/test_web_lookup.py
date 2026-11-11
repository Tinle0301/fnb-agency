"""Research looks the business up on the web before it works out the profile."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pytest

from app.llm import SearchResult
from app.memory.facts import InMemoryBrandMemory
from app.memory.session import InMemorySessionStore
from app.notify import Notifier
from app.orchestrator import Orchestrator
from app.schemas import ClientBrief, Decision, ResearchOutput
from tests.conftest import FakeLLM

pytestmark = pytest.mark.asyncio


@dataclass
class SearchingLLM(FakeLLM):
    searches: list[str] = field(default_factory=list)
    fail_search: bool = False

    async def search(self, *, system, prompt, model, max_searches=5):
        self.searches.append(prompt)
        if self.fail_search:
            raise RuntimeError("search unavailable")
        return SearchResult(
            "Found: Banh Mi Lab, 12 Tran Phu, Hoi An, Vietnam. A banh mi stall.",
            [{"title": "Banh Mi Lab on Maps", "url": "https://example.com/banh-mi-lab"}],
            model, 40, 20, 2,
        )


def orch(llm, settings):
    return Orchestrator(llm, InMemorySessionStore(), InMemoryBrandMemory(), settings, Notifier())


async def test_lookup_feeds_research_and_is_kept(settings):
    llm = SearchingLLM()
    o = orch(llm, settings)
    run = await o.advance((await o.start_run(ClientBrief(client_name="Banh Mi Lab", location="Hoi An"))).id)

    assert "'Banh Mi Lab'" in llm.searches[0] and "Hoi An" in llm.searches[0]
    research_prompt = llm.prompts_for(ResearchOutput)[0]
    assert "<web_lookup>" in research_prompt and "12 Tran Phu" in research_prompt
    assert run.outputs["lookup"]["sources"][0]["url"] == "https://example.com/banh-mi-lab"
    assert run.usage["input_tokens"] >= 40


async def test_reviewer_correction_reaches_the_next_lookup(settings):
    llm = SearchingLLM()
    o = orch(llm, settings)
    run = await o.advance((await o.start_run(ClientBrief(client_name="Banh Mi Lab"))).id)
    run = await o.decide(run.id, checkpoint="research", decision=Decision.request_changes, feedback="Wrong one: the bakery in Da Nang.")
    await o.advance(run.id)
    assert "the bakery in Da Nang" in llm.searches[1]
    assert "Type hint" not in llm.searches[1]  # research's own guess is not fed back as a hint


async def test_failed_lookup_does_not_stop_research(settings):
    llm = SearchingLLM(fail_search=True)
    o = orch(llm, settings)
    run = await o.advance((await o.start_run(ClientBrief(client_name="Banh Mi Lab"))).id)
    assert "research" in run.outputs and "lookup" not in run.outputs
    events = [e.kind for e in await o.sessions.get_events(run.id)]
    assert "research.lookup" in events


async def test_lookup_can_be_turned_off(settings):
    llm = SearchingLLM()
    o = orch(llm, replace(settings, web_lookup=False))
    await o.advance((await o.start_run(ClientBrief(client_name="Banh Mi Lab"))).id)
    assert llm.searches == []


async def test_anthropic_search_resumes_paused_turns_and_collects_sources():
    from types import SimpleNamespace as NS

    from app.llm import AnthropicLLM

    hit = NS(type="web_search_result", url="https://example.com/a", title="A")
    turns = [
        NS(stop_reason="pause_turn", usage=NS(input_tokens=10, output_tokens=5),
           content=[NS(type="server_tool_use"), NS(type="web_search_tool_result", content=[hit])]),
        NS(stop_reason="end_turn", usage=NS(input_tokens=7, output_tokens=3),
           content=[NS(type="web_search_tool_result", content={"error_code": "max_uses_exceeded"}), NS(type="text", text="Found it.")]),
    ]
    sent = []

    async def create(**kwargs):
        sent.append(kwargs["messages"])
        return turns[len(sent) - 1]

    client = NS(messages=NS(create=create))
    found = await AnthropicLLM(client=client).search(system="s", prompt="find", model="m")
    assert found.text == "Found it." and found.sources == [{"title": "A", "url": "https://example.com/a"}]
    assert (found.input_tokens, found.searches) == (17, 1)
    assert sent[1][1]["role"] == "assistant" and len(sent[1]) == 2  # resumed, no extra "continue" message
