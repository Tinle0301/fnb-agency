"""A brand report can start from a business name alone."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.memory.facts import InMemoryBrandMemory
from app.memory.session import InMemorySessionStore
from app.notify import Notifier
from app.orchestrator import Orchestrator, current_checkpoint
from app.schemas import ClientBrief, Decision, ResearchOutput
from evals import fixtures as fx

pytestmark = pytest.mark.asyncio


def guessed(**profile) -> ResearchOutput:
    data = fx.BREWERY_RESEARCH.model_dump()
    data["business_profile"].update(profile)
    return ResearchOutput.model_validate(data)


async def test_name_alone_is_a_valid_brief():
    brief = ClientBrief(client_name="Banh Mi Lab")
    assert brief.client_id == "banh-mi-lab"
    assert brief.blank_fields() == ["business_type", "location", "target_audience", "goals"]


async def test_research_fills_the_blank_brief_fields(orchestrator, llm):
    llm.script(ResearchOutput, guessed(business_type="street food kiosk", location="Da Nang, Vietnam"))
    run = await orchestrator.advance((await orchestrator.start_run(ClientBrief(client_name="Banh Mi Lab", location="Hoi An"))).id)

    assert current_checkpoint(run) == "research"
    assert run.brief.business_type == "street food kiosk"
    assert run.brief.location == "Hoi An"  # typed by the person, never overwritten
    assert run.brief.goals == fx.BREWERY_BRIEF.goals
    assert run.inferred == ["business_type", "target_audience", "goals"]


async def test_research_rerun_updates_only_the_guesses(orchestrator, llm):
    llm.script(ResearchOutput, guessed(business_type="street food kiosk"), guessed(business_type="banh mi bakery"))
    run = await orchestrator.advance((await orchestrator.start_run(ClientBrief(client_name="Banh Mi Lab", location="Hoi An"))).id)
    run = await orchestrator.decide(run.id, checkpoint="research", decision=Decision.request_changes, feedback="It is a bakery.")
    run = await orchestrator.advance(run.id)

    assert run.brief.business_type == "banh mi bakery"
    assert run.brief.location == "Hoi An"


async def test_default_is_one_research_check_then_final_sign_off(llm):
    settings = Settings(storage="memory")
    assert settings.checkpoints == {"research", "final"}
    orch = Orchestrator(llm, InMemorySessionStore(), InMemoryBrandMemory(), settings, Notifier())
    run = await orch.advance((await orch.start_run(ClientBrief(client_name="Banh Mi Lab"))).id)
    assert current_checkpoint(run) == "research"
    run = await orch.advance((await orch.decide(run.id, checkpoint="research", decision=Decision.approve)).id)
    assert current_checkpoint(run) == "final"
    assert {"strategy", "messaging", "identity", "report", "qa"} <= set(run.outputs)
