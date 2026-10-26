"""End to end over HTTP with the fake model and in-memory stores."""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from evals import fixtures as fx


@pytest.fixture
def client(orchestrator, settings):
    with TestClient(create_app(orchestrator, settings)) as c:
        yield c


def step(client, run_id, checkpoint, **body):
    r = client.post(f"/runs/{run_id}/decision", json={"checkpoint": checkpoint, "decision": "approve", **body})
    assert r.status_code == 200, r.text
    return client.get(f"/runs/{run_id}").json()


def test_full_engagement_over_http(client):
    r = client.post("/runs", json=fx.BREWERY_BRIEF.model_dump())
    assert r.status_code == 202
    run_id = r.json()["run"]["id"]

    view = client.get(f"/runs/{run_id}").json()
    assert view["open_checkpoint"] == "research" and view["zone"] == "needs_you"
    assert client.get("/runs").json()["needs_you"][0]["run"]["id"] == run_id

    view = step(client, run_id, "research", answers=[{"question": "Locals first?", "answer": "Yes"}])
    view = step(client, run_id, "strategy")
    assert view["open_checkpoint"] == "final"

    report = client.get(f"/runs/{run_id}/report.md")
    assert report.status_code == 200 and report.text.startswith("# Harbor Hops Brewing")

    view = step(client, run_id, "final")
    assert view["run"]["status"] == "completed" and view["zone"] == "done"

    pending = client.get("/clients/harbor-hops/facts", params={"status": "pending"}).json()
    confirmed = client.post(f"/facts/{pending[0]['id']}/review", json={"status": "active"}).json()
    assert confirmed["status"] == "active"

    kinds = [e["kind"] for e in client.get(f"/runs/{run_id}/events").json()]
    assert kinds[0] == "run.created" and kinds[-1] == "run.completed"


def test_stale_decision_is_a_conflict(client):
    run_id = client.post("/runs", json=fx.BREWERY_BRIEF.model_dump()).json()["run"]["id"]
    r = client.post(f"/runs/{run_id}/decision", json={"checkpoint": "strategy", "decision": "approve"})
    assert r.status_code == 409


def test_design_system_export_is_an_opendesign_package(client):
    run_id = client.post("/runs", json=fx.BREWERY_BRIEF.model_dump()).json()["run"]["id"]
    for cp in ("research", "strategy"):
        step(client, run_id, cp)
    r = client.get(f"/runs/{run_id}/design-system.zip")
    assert r.status_code == 200
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = set(zf.namelist())
        assert names == {"harbor-hops-brewing/manifest.json", "harbor-hops-brewing/DESIGN.md", "harbor-hops-brewing/tokens.css"}
        manifest = json.loads(zf.read("harbor-hops-brewing/manifest.json"))
        tokens = zf.read("harbor-hops-brewing/tokens.css").decode()
        design = zf.read("harbor-hops-brewing/DESIGN.md").decode()
    assert manifest["schemaVersion"] == "od-design-system-project/v1" and manifest["id"] == "harbor-hops-brewing"
    assert "--accent: #1F5C5A;" in tokens
    for heading in ("## 2. Color", "## 3. Typography", "## 8. Voice & Brand", "## 9. Anti-patterns"):
        assert heading in design


def test_unknown_run_is_404(client):
    assert client.get("/runs/nope").status_code == 404


def test_failed_run_can_be_retried(client, llm):
    from app.schemas import ResearchOutput

    llm.fail_on = ResearchOutput
    run_id = client.post("/runs", json=fx.BREWERY_BRIEF.model_dump()).json()["run"]["id"]
    assert client.get(f"/runs/{run_id}").json()["run"]["status"] == "failed"
    llm.fail_on = None
    client.post(f"/runs/{run_id}/retry")
    assert client.get(f"/runs/{run_id}").json()["open_checkpoint"] == "research"


def test_dashboard_is_served(client):
    assert "Agency Dashboard" in client.get("/").text


def test_settings_tell_the_dashboard_which_checkpoints_exist(client):
    body = client.get("/settings").json()
    assert set(body["checkpoints"]) == {"research", "strategy", "final"}
    assert body["max_qa_revisions"] >= 1


def test_clients_list_counts_facts(client):
    run_id = client.post("/runs", json=fx.BREWERY_BRIEF.model_dump()).json()["run"]["id"]
    step(client, run_id, "research")
    step(client, run_id, "strategy")
    step(client, run_id, "final")
    [summary] = client.get("/clients").json()
    assert summary["id"] == fx.BREWERY_BRIEF.client_id
    assert summary["active_facts"] + summary["pending_facts"] > 0
