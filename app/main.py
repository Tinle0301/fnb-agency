"""FastAPI app: start runs, review checkpoints, browse brand memory, export deliverables."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from app.config import Settings
from app.exports import (
    brand_guideline_md,
    design_system_files,
    design_system_zip,
    report_markdown,
    seo_brief_md,
    slugify,
)
from app.llm import LLM, AnthropicLLM
from app.logging_setup import configure_logging, get_logger
from app.memory.facts import BrandMemory, InMemoryBrandMemory, PostgresBrandMemory
from app.memory.session import InMemorySessionStore, RedisSessionStore, SessionStore
from app.notify import Notifier
from app.orchestrator import (
    InvalidDecision,
    Orchestrator,
    RunNotFound,
    current_checkpoint,
)
from app.schemas import (
    BrandFact,
    ClientAnswer,
    ClientSummary,
    ClientBrief,
    Decision,
    FactStatus,
    IdentityOutput,
    MessagingOutput,
    ReportOutput,
    Run,
    RunEvent,
    RunStatus,
    StrategyOutput,
)

log = get_logger(__name__)
STATIC_DIR = Path(__file__).parent / "static"


# --------------------------------------------------------------------------- request/response models


class DecisionRequest(BaseModel):
    checkpoint: str = Field(description="The checkpoint being decided; must be the one currently open.")
    decision: Decision
    feedback: str = ""
    answers: list[ClientAnswer] = []
    direction: int | None = Field(
        default=None, description="Creative checkpoint only: which identity direction to keep (0-based)."
    )
    actor: str = "strategist"


class FactReview(BaseModel):
    status: FactStatus


class ActivityItem(BaseModel):
    """One run event with the engagement it belongs to, for the dashboard's live log."""

    run_id: str
    client_name: str
    at: datetime
    kind: str
    stage: str | None = None
    actor: str = "system"
    detail: dict[str, Any] = {}


class RunView(BaseModel):
    run: Run
    open_checkpoint: str | None
    zone: str


# Board lanes, after agent-orchestrator's attention zones: what needs a person sorts first.
ZONE_ORDER = ["needs_you", "working", "done"]


def zone_of(run: Run) -> str:
    if run.status in (RunStatus.awaiting_approval, RunStatus.failed):
        return "needs_you"
    if run.status is RunStatus.running:
        return "working"
    return "done"


def view(run: Run) -> RunView:
    return RunView(run=run, open_checkpoint=current_checkpoint(run), zone=zone_of(run))


# --------------------------------------------------------------------------- wiring


async def build_orchestrator(settings: Settings, llm: LLM | None = None) -> Orchestrator:
    sessions: SessionStore
    memory: BrandMemory
    if settings.storage == "memory":
        sessions, memory = InMemorySessionStore(), InMemoryBrandMemory()
    else:
        sessions = RedisSessionStore(settings.redis_url, settings.session_ttl_seconds)
        pg = PostgresBrandMemory(settings.database_url)
        await pg.open()
        memory = pg
    if llm is None and settings.demo:
        from app.demo import DemoLLM

        llm = DemoLLM()
    if llm is None and not (settings.agent_model and settings.extractor_model):
        raise RuntimeError("Set AGENCY_MODEL and EXTRACTOR_MODEL in .env (or AGENCY_DEMO=1 to try without a model).")
    return Orchestrator(
        llm or AnthropicLLM(use_refusal_fallbacks=settings.use_refusal_fallbacks),
        sessions,
        memory,
        settings,
        Notifier(settings.notify_webhook_url, settings.public_base_url),
    )


def create_app(orchestrator: Orchestrator | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.log_level)
        app.state.orchestrator = orchestrator or await build_orchestrator(settings)
        log.info("app.started", storage=settings.storage, model=settings.agent_model, demo=settings.demo)
        yield
        await app.state.orchestrator.sessions.close()
        await app.state.orchestrator.memory.close()

    app = FastAPI(title="F&B Virtual Agency", version="1.0.0", lifespan=lifespan)

    def orch(request: Request) -> Orchestrator:
        return request.app.state.orchestrator

    async def load(run_id: str, o: Orchestrator) -> Run:
        try:
            return await o.get_run(run_id)
        except RunNotFound:
            raise HTTPException(404, f"run {run_id} not found")

    @app.get("/", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(STATIC_DIR / "dashboard.html")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/runs", status_code=202, response_model=RunView)
    async def start_run(brief: ClientBrief, tasks: BackgroundTasks, o: Orchestrator = Depends(orch)) -> RunView:
        run = await o.start_run(brief)
        tasks.add_task(o.advance, run.id)
        return view(run)

    @app.get("/runs", response_model=dict[str, list[RunView]])
    async def board(o: Orchestrator = Depends(orch)) -> dict[str, list[RunView]]:
        lanes: dict[str, list[RunView]] = {z: [] for z in ZONE_ORDER}
        for run in await o.list_runs():
            lanes[zone_of(run)].append(view(run))
        return lanes

    @app.get("/runs/{run_id}", response_model=RunView)
    async def get_run(run_id: str, o: Orchestrator = Depends(orch)) -> RunView:
        return view(await load(run_id, o))

    @app.get("/runs/{run_id}/events", response_model=list[RunEvent])
    async def get_events(run_id: str, o: Orchestrator = Depends(orch)) -> list[RunEvent]:
        await load(run_id, o)
        return await o.sessions.get_events(run_id)

    @app.get("/activity", response_model=list[ActivityItem])
    async def activity(limit: int = 300, runs: int = 25, o: Orchestrator = Depends(orch)) -> list[ActivityItem]:
        """Recent events across the latest engagements, oldest first: the dashboard's live log."""
        limit, runs = max(1, min(limit, 1000)), max(1, min(runs, 100))
        items: list[ActivityItem] = []
        for run in await o.list_runs(runs):
            for event in await o.sessions.get_events(run.id):
                items.append(ActivityItem(run_id=run.id, client_name=run.brief.client_name, **event.model_dump()))
        items.sort(key=lambda item: item.at)
        return items[-limit:]

    @app.post("/runs/{run_id}/decision", response_model=RunView)
    async def decide(
        run_id: str, body: DecisionRequest, tasks: BackgroundTasks, o: Orchestrator = Depends(orch)
    ) -> RunView:
        await load(run_id, o)
        try:
            run = await o.decide(
                run_id,
                checkpoint=body.checkpoint,
                decision=body.decision,
                feedback=body.feedback,
                answers=body.answers,
                direction=body.direction,
                actor=body.actor,
            )
        except InvalidDecision as exc:
            raise HTTPException(409, str(exc))
        if run.status is RunStatus.running:
            tasks.add_task(o.advance, run.id)
        return view(run)

    @app.post("/runs/{run_id}/retry", response_model=RunView)
    async def retry(run_id: str, tasks: BackgroundTasks, o: Orchestrator = Depends(orch)) -> RunView:
        """Re-run the stage that failed (e.g. after an API outage)."""
        run = await load(run_id, o)
        if run.status is not RunStatus.failed:
            raise HTTPException(409, f"run is {run.status.value}, only failed runs can be retried")
        run.status, run.error = RunStatus.running, None
        await o.sessions.save_run(run)
        tasks.add_task(o.advance, run.id)
        return view(run)

    @app.get("/runs/{run_id}/report.md", response_class=PlainTextResponse)
    async def report_md(run_id: str, o: Orchestrator = Depends(orch)) -> str:
        run = await load(run_id, o)
        if "report" not in run.outputs:
            raise HTTPException(404, "report not produced yet")
        return report_markdown(ReportOutput.model_validate(run.outputs["report"]))

    @app.get("/runs/{run_id}/design-system")
    async def design_system(run_id: str, o: Orchestrator = Depends(orch)) -> dict[str, Any]:
        """The approved identity as an OpenDesign design-system package (manifest, DESIGN.md, tokens.css)."""
        run = await load(run_id, o)
        return {"slug": slugify(run.brief.client_name), "files": _design_files(run)}

    @app.get("/runs/{run_id}/design-system.zip")
    async def design_system_download(run_id: str, o: Orchestrator = Depends(orch)) -> Response:
        run = await load(run_id, o)
        slug = slugify(run.brief.client_name)
        data = design_system_zip(_design_files(run), slug)
        return Response(
            data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{slug}-design-system.zip"'},
        )

    @app.get("/runs/{run_id}/brand-guideline.md", response_class=PlainTextResponse)
    async def brand_guideline(run_id: str, o: Orchestrator = Depends(orch)) -> str:
        """Production guideline for a designer or an AI design tool (also inside the .zip)."""
        run = await load(run_id, o)
        return brand_guideline_md(*_approved_inputs(run))

    @app.get("/runs/{run_id}/seo-brief.md", response_class=PlainTextResponse)
    async def seo_brief(run_id: str, o: Orchestrator = Depends(orch)) -> str:
        """Search starter kit for the site builder: keywords, titles, JSON-LD, Business Profile (also in the .zip)."""
        run = await load(run_id, o)
        return seo_brief_md(*_approved_inputs(run))

    @app.get("/settings")
    async def public_settings(o: Orchestrator = Depends(orch)) -> dict[str, Any]:
        """Workflow settings the dashboard shows (no secrets, no model IDs)."""
        s = o.settings
        return {
            "checkpoints": sorted(s.checkpoints),
            "max_qa_revisions": s.max_qa_revisions,
            "fact_auto_save_threshold": s.fact_auto_save_threshold,
            "fact_review_threshold": s.fact_review_threshold,
            "demo": s.demo,
            "storage": s.storage,
        }

    @app.get("/clients", response_model=list[ClientSummary])
    async def clients(o: Orchestrator = Depends(orch)) -> list[ClientSummary]:
        return await o.memory.list_clients()

    @app.get("/clients/{client_id}/facts", response_model=list[BrandFact])
    async def client_facts(
        client_id: str, status: FactStatus | None = None, o: Orchestrator = Depends(orch)
    ) -> list[BrandFact]:
        return await o.memory.get_facts(client_id, status)

    @app.post("/facts/{fact_id}/review", response_model=BrandFact)
    async def review_fact(fact_id: int, body: FactReview, o: Orchestrator = Depends(orch)) -> BrandFact:
        """Confirm (active) or reject a pending fact."""
        fact = await o.memory.set_fact_status(fact_id, body.status)
        if fact is None:
            raise HTTPException(404, f"fact {fact_id} not found")
        log.info("fact.reviewed", fact_id=fact_id, status=body.status.value)
        return fact

    return app


def _approved_inputs(run: Run) -> tuple[ClientBrief, StrategyOutput, MessagingOutput, IdentityOutput]:
    missing = [k for k in ("strategy", "messaging", "identity") if k not in run.outputs]
    if missing:
        raise HTTPException(404, f"identity not produced yet (missing: {', '.join(missing)})")
    return (
        run.brief,
        StrategyOutput.model_validate(run.outputs["strategy"]),
        MessagingOutput.model_validate(run.outputs["messaging"]),
        IdentityOutput.model_validate(run.outputs["identity"]),
    )


def _design_files(run: Run) -> dict[str, str]:
    return design_system_files(*_approved_inputs(run))


app = create_app()
