from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app import checks
from app.main import create_app
from app.orchestrator import current_checkpoint, owner_of
from app.schemas import Decision, QAOutput, ReportOutput, RunStatus, SocialOutput
from evals import fixtures as fx


async def to_final(orch):
    run = await orch.advance((await orch.start_run(fx.BREWERY_BRIEF)).id)
    while current_checkpoint(run) != "final":
        run = await orch.decide(run.id, checkpoint=current_checkpoint(run), decision=Decision.approve)
        run = await orch.advance(run.id)
    return run


@pytest.mark.asyncio
async def test_social_plan_runs_after_creative_and_feeds_the_report(orchestrator, llm):
    run = await to_final(orchestrator)
    assert run.outputs["social"]["scripts"][0]["title"] == "Dawn on the pier"
    social_prompt = llm.prompts_for(SocialOutput)[0]
    assert "approved_messaging" in social_prompt and "approved_identity" in social_prompt
    assert "Dawn on the pier" in llm.prompts_for(ReportOutput)[0]


@pytest.mark.asyncio
async def test_qa_issue_in_social_goes_to_the_social_strategist(orchestrator, llm):
    fail = QAOutput(
        passed=False,
        score=5,
        issues=[{"severity": "major", "location": "social.scripts", "problem": "Hook is too slow.", "suggested_fix": "Open on the pour."}],
        summary="One script issue.",
    )
    llm.script(QAOutput, fail, fx.QA_PASS)
    await to_final(orchestrator)
    prompts = llm.prompts_for(SocialOutput)
    assert len(prompts) == 2 and "Hook is too slow." in prompts[1]


@pytest.mark.asyncio
async def test_sign_off_notes_reach_the_social_strategist(orchestrator, llm):
    run = await to_final(orchestrator)
    await orchestrator.decide(run.id, checkpoint="final", decision=Decision.request_changes, feedback="Add a script for Tet.")
    run = await orchestrator.advance(run.id)
    assert "Add a script for Tet." in llm.prompts_for(SocialOutput)[-1]
    assert run.status is RunStatus.awaiting_approval


def test_owner_of_social_location():
    assert owner_of("social.scripts[2].hook") == "social"


def test_social_checks():
    assert checks.check_social(fx.BREWERY_SOCIAL) == []
    bad = fx.BREWERY_SOCIAL.model_copy(update={"scripts": fx.BREWERY_SOCIAL.scripts[:2]})
    bad.scripts[0] = bad.scripts[0].model_copy(update={"caption": "This beer boosts immunity."})
    found = checks.check_social(bad)
    assert any(f.location == "social.scripts" and f.severity == "major" for f in found)
    assert any(f.severity == "blocker" for f in found)


def test_social_plan_download_and_zip(orchestrator, settings):
    with TestClient(create_app(orchestrator, settings)) as client:
        run_id = client.post("/runs", json=fx.BREWERY_BRIEF.model_dump()).json()["run"]["id"]
        assert client.get(f"/runs/{run_id}/social-plan.md").status_code == 404
        for cp in ("research", "strategy", "creative"):
            client.post(f"/runs/{run_id}/decision", json={"checkpoint": cp, "decision": "approve"})
        plan = client.get(f"/runs/{run_id}/social-plan.md")
        assert plan.status_code == 200
        assert plan.text.startswith("# Harbor Hops Brewing: social media plan")
        assert "| 0-3s |" in plan.text and "## Four-week calendar" in plan.text
        z = zipfile.ZipFile(io.BytesIO(client.get(f"/runs/{run_id}/design-system.zip").content))
        assert any(n.endswith("/SOCIAL_PLAN.md") for n in z.namelist())


def test_calendar_platform_must_match_the_script_and_no_bracket_blanks():
    cal = [c.model_copy() for c in fx.BREWERY_SOCIAL.calendar]
    cal[0] = cal[0].model_copy(update={"platform": "Facebook"})  # "Dawn on the pier" is an Instagram script
    scripts = list(fx.BREWERY_SOCIAL.scripts)
    scripts[1] = scripts[1].model_copy(update={"caption": "Find us at [địa chỉ quán]."})
    found = checks.check_social(fx.BREWERY_SOCIAL.model_copy(update={"calendar": cal, "scripts": scripts}))
    assert any("Dawn on the pier" in f.problem and f.location == "social.calendar" for f in found)
    assert any("bracketed blank" in f.problem for f in found)
