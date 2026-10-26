"""The orchestrator: runs the six agents in order and stops at human checkpoints.

Pipeline (checkpoint names in brackets; which ones pause is configurable, "final" always does):

    research ─[research]→ strategy ─[strategy]→ creative ─[creative]→ report+QA ─[final]→ facts
                                                (messaging ∥ identity)

At a checkpoint the run waits in `awaiting_approval`. A person can approve (move on),
request changes (re-run the same stage with their feedback in the prompt), or reject.
The report stage loops Report Producer → automated checks → QA Reviewer, feeding QA
issues back to the producer, up to `max_qa_revisions` times. If QA still fails, the
run goes to the final checkpoint flagged `qa_escalated` so a person decides.
After final approval the fact extractor stores durable facts in long-term memory.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel

from app import checks
from app.agents import (
    BrandStrategist,
    IdentityDirection,
    MessagingLead,
    QAReviewer,
    ReportProducer,
    ResearchAnalyst,
)
from app.agents.base import Agent, AgentContext, AgentResult
from app.config import Settings
from app.llm import LLM
from app.logging_setup import get_logger, log_context
from app.memory.extractor import FactExtractor, triage_facts
from app.memory.facts import BrandMemory
from app.memory.session import SessionStore
from app.notify import Notifier
from app.schemas import (
    STAGE_ORDER,
    ClientAnswer,
    ClientBrief,
    Decision,
    FactStatus,
    IdentityOutput,
    MessagingOutput,
    QAOutput,
    ReportOutput,
    ResearchOutput,
    Run,
    RunEvent,
    RunStatus,
    Stage,
    StrategyOutput,
)

log = get_logger(__name__)

OUTPUT_TYPES: dict[str, type[BaseModel]] = {
    "research": ResearchOutput,
    "strategy": StrategyOutput,
    "messaging": MessagingOutput,
    "identity": IdentityOutput,
    "report": ReportOutput,
    "qa": QAOutput,
}

# The checkpoint that follows each stage. Fact extraction has none.
CHECKPOINT_AFTER: dict[Stage, str | None] = {
    Stage.research: "research",
    Stage.strategy: "strategy",
    Stage.creative: "creative",
    Stage.report: "final",
    Stage.final: None,
}


class RunNotFound(LookupError):
    pass


class InvalidDecision(ValueError):
    pass


def next_stage(stage: Stage) -> Stage:
    idx = STAGE_ORDER.index(stage)
    return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else Stage.done


def owner_of(location: str) -> str:
    """Which deliverable a QA issue location points at: messaging, identity, or report."""
    head = location.strip().lower()
    for owner in ("messaging", "identity"):
        if head.startswith(owner):
            return owner
    return "report"


def current_checkpoint(run: Run) -> str | None:
    if run.status is not RunStatus.awaiting_approval:
        return None
    return CHECKPOINT_AFTER.get(run.stage)


class Orchestrator:
    def __init__(
        self,
        llm: LLM,
        sessions: SessionStore,
        memory: BrandMemory,
        settings: Settings,
        notifier: Notifier | None = None,
    ) -> None:
        self.notifier = notifier or Notifier()
        self.sessions = sessions
        self.memory = memory
        self.settings = settings
        model, effort = settings.agent_model, settings.agent_effort
        self.research = ResearchAnalyst(llm, model, effort)
        self.strategist = BrandStrategist(llm, model, effort)
        self.messaging = MessagingLead(llm, model, effort)
        self.identity = IdentityDirection(llm, model, effort)
        self.reporter = ReportProducer(llm, model, effort)
        self.qa = QAReviewer(llm, model, effort)
        self.extractor = FactExtractor(llm, settings.extractor_model, settings.extractor_effort)
        self._locks: dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------ public API

    async def start_run(self, brief: ClientBrief) -> Run:
        await self.memory.ensure_client(brief.client_id, brief.client_name)
        run = Run(brief=brief)
        await self.sessions.save_run(run)
        await self._event(run, "run.created", detail={"client_name": brief.client_name})
        with log_context(run_id=run.id, client_id=run.client_id):
            log.info("run.created", business_type=brief.business_type)
        return run

    async def list_runs(self, limit: int = 100) -> list[Run]:
        return await self.sessions.list_runs(limit)

    async def get_run(self, run_id: str) -> Run:
        run = await self.sessions.get_run(run_id)
        if run is None:
            raise RunNotFound(run_id)
        return run

    async def advance(self, run_id: str) -> Run:
        """Run stages until the next checkpoint, completion, or failure."""
        async with self._lock(run_id):
            run = await self.get_run(run_id)
            with log_context(run_id=run.id, client_id=run.client_id):
                while run.status is RunStatus.running and run.stage is not Stage.done:
                    with log_context(stage=run.stage.value):
                        try:
                            await self._execute_stage(run)
                        except Exception as exc:
                            run.status = RunStatus.failed
                            run.error = f"{type(exc).__name__}: {exc}"
                            log.error("stage.failed", exc_info=True, error=run.error)
                            await self._event(run, "stage.failed", detail={"error": run.error})
                            await self.sessions.save_run(run)
                            await self.notifier.needs_you(
                                run_id=run.id,
                                client_name=run.brief.client_name,
                                reason=f"{run.stage.value} stage failed: {run.error}",
                            )
                            break

                        checkpoint = CHECKPOINT_AFTER[run.stage]
                        if checkpoint and checkpoint in self.settings.checkpoints:
                            run.status = RunStatus.awaiting_approval
                            log.info("checkpoint.opened", checkpoint=checkpoint)
                            await self._event(run, "checkpoint.opened", detail={"checkpoint": checkpoint})
                            reason = f"{checkpoint} checkpoint is ready for review"
                            if run.qa_escalated:
                                reason += " (QA did not pass; review its issues)"
                            await self.notifier.needs_you(
                                run_id=run.id, client_name=run.brief.client_name, reason=reason
                            )
                        elif run.stage is Stage.final:
                            run.stage = Stage.done
                            run.status = RunStatus.completed
                            log.info("run.completed", **run.usage)
                            await self._event(run, "run.completed", detail=dict(run.usage))
                        else:
                            run.stage = next_stage(run.stage)
                        await self.sessions.save_run(run)
            return run

    async def decide(
        self,
        run_id: str,
        *,
        checkpoint: str,
        decision: Decision,
        feedback: str = "",
        answers: list[ClientAnswer] | None = None,
        actor: str = "human",
    ) -> Run:
        """Record a human decision at the open checkpoint. Call advance() afterwards.

        At the research checkpoint, `answers` carries the client's replies to the Research
        Analyst's clarifying questions; every later agent sees them.
        """
        async with self._lock(run_id):
            run = await self.get_run(run_id)
            open_checkpoint = current_checkpoint(run)
            if open_checkpoint is None:
                raise InvalidDecision(f"run is {run.status.value}, not awaiting approval")
            if checkpoint != open_checkpoint:
                raise InvalidDecision(
                    f"checkpoint '{checkpoint}' is not open; the open checkpoint is '{open_checkpoint}'"
                )
            if decision is Decision.request_changes and not feedback.strip():
                raise InvalidDecision("request_changes needs feedback describing what to change")
            if answers and checkpoint != "research":
                raise InvalidDecision("answers to clarifying questions are taken at the research checkpoint")

            with log_context(run_id=run.id, client_id=run.client_id, stage=run.stage.value):
                await self.memory.record_decision(
                    run.id, run.client_id, checkpoint, decision.value, feedback, actor
                )
                await self._event(
                    run,
                    "checkpoint.decided",
                    actor=actor,
                    detail={
                        "checkpoint": checkpoint,
                        "decision": decision.value,
                        "feedback": feedback,
                        "answers": [a.model_dump() for a in answers or []],
                    },
                )
                log.info("checkpoint.decided", checkpoint=checkpoint, decision=decision.value, actor=actor)

                if answers:
                    run.answers = [*run.answers, *answers]
                if decision is Decision.approve:
                    run.stage = next_stage(run.stage)
                    run.status = RunStatus.running
                elif decision is Decision.request_changes:
                    run.feedback.setdefault(run.stage.value, []).append(feedback.strip())
                    run.status = RunStatus.running
                else:
                    run.status = RunStatus.rejected
                await self.sessions.save_run(run)
            return run

    # ------------------------------------------------------------------ stages

    async def _execute_stage(self, run: Run) -> None:
        log.info("stage.started")
        await self._event(run, "stage.started")
        if run.stage is Stage.research:
            result = await self._run_agent(run, self.research, run.feedback.get("research", []))
            run.outputs["research"] = result.output.model_dump()
        elif run.stage is Stage.strategy:
            result = await self._run_agent(run, self.strategist, run.feedback.get("strategy", []))
            run.outputs["strategy"] = result.output.model_dump()
        elif run.stage is Stage.creative:
            feedback = run.feedback.get("creative", [])
            messaging, identity = await asyncio.gather(
                self._run_agent(run, self.messaging, feedback),
                self._run_agent(run, self.identity, feedback),
            )
            run.outputs["messaging"] = messaging.output.model_dump()
            run.outputs["identity"] = identity.output.model_dump()
        elif run.stage is Stage.report:
            await self._report_with_qa(run)
        elif run.stage is Stage.final:
            await self._extract_facts(run)
        await self._event(run, "stage.completed")
        log.info("stage.completed")

    async def _report_with_qa(self, run: Run) -> None:
        """Report Producer -> automated checks -> QA Reviewer, with issues routed to their owner.

        Each blocker/major issue goes back to the agent that owns the deliverable it is in
        (messaging, identity, or the report itself), so a bad tagline is fixed by the
        Messaging Lead rather than papered over in the report.
        """
        human_feedback = run.feedback.get("report", [])
        report_fixes: list[str] = []
        alcohol = checks.is_alcohol_brand(run.brief.business_type)
        passed = False
        attempts = 0

        for attempt in range(self.settings.max_qa_revisions + 1):
            attempts = attempt + 1
            report_result = await self._run_agent(run, self.reporter, human_feedback + report_fixes)
            report = report_result.output
            outputs = self._typed_outputs(run)

            findings = (
                checks.check_report(report, alcohol)
                + checks.check_messaging(outputs["messaging"], alcohol)
                + checks.check_identity(outputs["identity"])
            )
            automated = [f.__dict__ for f in findings]
            ctx = await self._context(run, extra={"automated_findings": automated})
            ctx.outputs["report"] = report
            qa_result = await self._timed(run, self.qa, ctx)
            qa: QAOutput = qa_result.output

            gating_issues = [i for i in qa.issues if i.severity in ("blocker", "major")]
            automated_blockers = [f for f in findings if f.severity == "blocker"]
            passed = qa.passed and not gating_issues and not automated_blockers

            log.info(
                "qa.reviewed",
                attempt=attempts,
                passed=passed,
                model_passed=qa.passed,
                score=qa.score,
                blockers=sum(i.severity == "blocker" for i in qa.issues),
                majors=sum(i.severity == "major" for i in qa.issues),
                automated_blockers=len(automated_blockers),
            )
            await self._event(
                run,
                "qa.reviewed",
                detail={"attempt": attempts, "passed": passed, "score": qa.score, "summary": qa.summary},
            )
            run.outputs["report"] = report.model_dump()
            run.outputs["qa"] = {
                **qa.model_dump(),
                "automated_findings": automated,
                "gate_passed": passed,
                "attempts": attempts,
            }
            if passed or attempt == self.settings.max_qa_revisions:
                break

            routed: dict[str, list[str]] = {"messaging": [], "identity": [], "report": []}
            for issue in gating_issues:
                note = f"QA {issue.severity} in {issue.location}: {issue.problem} Fix: {issue.suggested_fix}"
                routed[owner_of(issue.location)].append(note)
            for finding in automated_blockers:
                routed[owner_of(finding.location)].append(f"Automated check ({finding.location}): {finding.problem}")
            await self._revise_creative(run, routed["messaging"], routed["identity"])
            report_fixes = routed["report"]

        run.qa_attempts = attempts
        run.qa_escalated = not passed
        if not passed:
            log.warning("qa.escalated", attempts=attempts)
            await self._event(run, "qa.escalated", detail={"attempts": attempts})

    async def _revise_creative(self, run: Run, messaging_fixes: list[str], identity_fixes: list[str]) -> None:
        jobs = []
        if messaging_fixes:
            jobs.append(("messaging", self.messaging, messaging_fixes))
        if identity_fixes:
            jobs.append(("identity", self.identity, identity_fixes))
        if not jobs:
            return
        prior = run.feedback.get("creative", [])
        results = await asyncio.gather(*(self._run_agent(run, agent, prior + fixes) for _, agent, fixes in jobs))
        for (key, agent, fixes), result in zip(jobs, results):
            run.outputs[key] = result.output.model_dump()
            log.info("qa.routed_revision", owner=agent.name, issues=len(fixes))
            await self._event(run, "qa.routed_revision", detail={"agent": agent.name, "issues": fixes})

    async def _extract_facts(self, run: Run) -> None:
        events = await self.sessions.get_events(run.id)
        human_feedback = [
            {"checkpoint": e.detail.get("checkpoint"), "decision": e.detail.get("decision"), "note": e.detail.get("feedback")}
            for e in events
            if e.kind == "checkpoint.decided" and e.detail.get("feedback")
        ]
        approved = {k: run.outputs[k] for k in ("research", "strategy", "messaging", "identity", "report")}
        ctx = await self._context(run, extra={"human_feedback": human_feedback, "approved_outputs": approved})
        result = await self._timed(run, self.extractor, ctx)

        triage = triage_facts(
            result.output.facts,
            client_id=run.client_id,
            run_id=run.id,
            auto_save_threshold=self.settings.fact_auto_save_threshold,
            review_threshold=self.settings.fact_review_threshold,
            approved_output_cap=self.settings.approved_output_confidence_cap,
        )
        await self.memory.save_facts(triage.to_save)
        summary = {"active": len(triage.active), "pending": len(triage.pending), "dropped": len(triage.dropped)}
        run.outputs["facts"] = summary
        log.info("facts.saved", **summary)
        await self._event(run, "facts.saved", detail=summary)

    # ------------------------------------------------------------------ helpers

    def _typed_outputs(self, run: Run) -> dict[str, Any]:
        return {k: OUTPUT_TYPES[k].model_validate(v) for k, v in run.outputs.items() if k in OUTPUT_TYPES}

    async def _context(self, run: Run, feedback: list[str] | None = None, extra: dict | None = None) -> AgentContext:
        facts = await self.memory.get_facts(run.client_id, FactStatus.active)
        return AgentContext(
            brief=run.brief,
            facts=facts,
            answers=run.answers,
            outputs=self._typed_outputs(run),
            feedback=feedback or [],
            extra=extra or {},
        )

    async def _run_agent(self, run: Run, agent: Agent, feedback: list[str]) -> AgentResult:
        return await self._timed(run, agent, await self._context(run, feedback))

    async def _timed(self, run: Run, agent: Agent, ctx: AgentContext) -> AgentResult:
        result = await agent.run(ctx)
        run.usage["input_tokens"] += result.llm.input_tokens
        run.usage["output_tokens"] += result.llm.output_tokens
        await self._event(
            run,
            "agent.completed",
            detail={
                "agent": agent.name,
                "latency_ms": result.latency_ms,
                "input_tokens": result.llm.input_tokens,
                "output_tokens": result.llm.output_tokens,
            },
        )
        return result

    async def _event(self, run: Run, kind: str, actor: str = "system", detail: dict | None = None) -> None:
        await self.sessions.append_event(
            run.id, RunEvent(kind=kind, stage=run.stage.value, actor=actor, detail=detail or {})
        )

    def _lock(self, run_id: str) -> asyncio.Lock:
        return self._locks.setdefault(run_id, asyncio.Lock())
