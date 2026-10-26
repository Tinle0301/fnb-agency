"""Live evaluation of each agent against the model API.

    python -m evals.run                     # every agent, 1 trial per case
    python -m evals.run --agent messaging --trials 3
    python -m evals.run --model <model-id>   # compare a different model

Every case gives the agent fixed upstream context from evals/fixtures.py, so each agent is
scored on its own work. Results print as a table and are written to evals/results/.
This calls the real API and costs money: roughly one agent call per case per trial.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.agents import (
    BrandStrategist,
    IdentityDirection,
    MessagingLead,
    QAReviewer,
    ReportProducer,
    ResearchAnalyst,
)
from app.agents.base import Agent, AgentContext
from app.checks import check_identity, check_messaging, check_report, is_alcohol_brand
from app.config import Settings
from app.llm import AnthropicLLM
from app.memory.extractor import FactExtractor
from evals import fixtures as fx
from evals.graders import GRADERS

RESULTS_DIR = Path(__file__).parent / "results"


@dataclass
class Case:
    agent: str
    name: str
    ctx: AgentContext
    upstream: dict = field(default_factory=dict)


def _ctx(brief, **outputs) -> AgentContext:
    return AgentContext(brief=brief, outputs=dict(outputs))


def _qa_ctx(messaging=fx.BREWERY_MESSAGING, report=fx.BREWERY_REPORT) -> AgentContext:
    ctx = _ctx(
        fx.BREWERY_BRIEF,
        research=fx.BREWERY_RESEARCH,
        strategy=fx.BREWERY_STRATEGY,
        messaging=messaging,
        identity=fx.BREWERY_IDENTITY,
        report=report,
    )
    alcohol = is_alcohol_brand(fx.BREWERY_BRIEF.business_type)
    findings = check_report(report, alcohol) + check_messaging(messaging, alcohol) + check_identity(fx.BREWERY_IDENTITY)
    ctx.extra["automated_findings"] = [f.__dict__ for f in findings]
    return ctx


def build_cases() -> list[Case]:
    b = fx.BREWERY_BRIEF
    planted_messaging = fx.BREWERY_MESSAGING.model_copy(
        update={"tagline_options": ["Boosts immunity with every sip.", *fx.BREWERY_MESSAGING.tagline_options[1:]]}
    )
    planted_report = fx.BREWERY_REPORT.model_copy(
        update={
            "executive_summary": fx.BREWERY_REPORT.executive_summary
            + " Harbor Hops is already voted the best brewery in New England by 9 out of 10 locals."
        }
    )
    extractor_ctx = _ctx(b)
    extractor_ctx.extra = {
        "human_feedback": [
            {"checkpoint": "creative", "decision": "approve", "note": "Owner says: never use anchors anywhere in the brand."},
            {"checkpoint": "research", "decision": "approve", "note": "Someone floated opening in Boston one day; nothing decided."},
        ],
        "approved_outputs": {
            k: v.model_dump()
            for k, v in {
                "strategy": fx.BREWERY_STRATEGY,
                "messaging": fx.BREWERY_MESSAGING,
                "identity": fx.BREWERY_IDENTITY,
            }.items()
        },
    }
    return [
        Case("research", "brewery", _ctx(b)),
        Case("research", "bakery", _ctx(fx.BAKERY_BRIEF)),
        Case("strategy", "brewery", _ctx(b, research=fx.BREWERY_RESEARCH)),
        Case(
            "messaging",
            "brewery",
            _ctx(b, research=fx.BREWERY_RESEARCH, strategy=fx.BREWERY_STRATEGY),
            {"strategy": fx.BREWERY_STRATEGY},
        ),
        Case("identity", "brewery", _ctx(b, research=fx.BREWERY_RESEARCH, strategy=fx.BREWERY_STRATEGY)),
        Case(
            "report",
            "brewery",
            _ctx(
                b,
                research=fx.BREWERY_RESEARCH,
                strategy=fx.BREWERY_STRATEGY,
                messaging=fx.BREWERY_MESSAGING,
                identity=fx.BREWERY_IDENTITY,
            ),
            {"messaging": fx.BREWERY_MESSAGING},
        ),
        Case("qa", "clean", _qa_ctx(), {"expect_pass": True}),
        Case(
            "qa",
            "planted-health-claim",
            _qa_ctx(messaging=planted_messaging),
            {"expect_pass": False, "planted_location": "messaging"},
        ),
        Case(
            "qa",
            "planted-invented-stat",
            _qa_ctx(report=planted_report),
            {"expect_pass": False, "planted_location": "report"},
        ),
        Case(
            "extractor",
            "brewery",
            extractor_ctx,
            {"must_save": ["lobstermen", "anchor"], "must_not_save": ["boston"]},
        ),
    ]


def build_agents(settings: Settings, model: str | None) -> dict[str, Agent]:
    llm = AnthropicLLM(use_refusal_fallbacks=settings.use_refusal_fallbacks)
    m, e = model or settings.agent_model, settings.agent_effort
    return {
        "research": ResearchAnalyst(llm, m, e),
        "strategy": BrandStrategist(llm, m, e),
        "messaging": MessagingLead(llm, m, e),
        "identity": IdentityDirection(llm, m, e),
        "report": ReportProducer(llm, m, e),
        "qa": QAReviewer(llm, m, e),
        "extractor": FactExtractor(llm, model or settings.extractor_model, settings.extractor_effort),
    }


async def run_case(agent: Agent, case: Case, settings: Settings) -> dict:
    started = time.perf_counter()
    try:
        result = await agent.run(case.ctx)
    except Exception as exc:  # an agent error is a failed case, not a crashed eval
        return {"agent": case.agent, "case": case.name, "error": str(exc), "checks": [], "passed": False}
    grader = GRADERS[case.agent]
    if case.agent == "extractor":
        checks = grader(case.ctx.brief, result.output, case.upstream, auto_save=settings.fact_auto_save_threshold)
    else:
        checks = grader(case.ctx.brief, result.output, case.upstream)
    return {
        "agent": case.agent,
        "case": case.name,
        "passed": all(c.passed for c in checks),
        "checks": [asdict(c) for c in checks],
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "input_tokens": result.llm.input_tokens,
        "output_tokens": result.llm.output_tokens,
        "output": result.output.model_dump(),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--agent", choices=sorted(GRADERS) + ["all"], default="all")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--model", default=None, help="override the model for every agent")
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    settings = Settings.from_env()
    if not args.model and not (settings.agent_model and settings.extractor_model):
        parser.error("set AGENCY_MODEL and EXTRACTOR_MODEL in .env, or pass --model")
    agents = build_agents(settings, args.model)
    cases = [c for c in build_cases() if args.agent in ("all", c.agent)]
    sem = asyncio.Semaphore(args.concurrency)

    async def bounded(case: Case) -> dict:
        async with sem:
            return await run_case(agents[case.agent], case, settings)

    results = await asyncio.gather(*(bounded(c) for c in cases for _ in range(args.trials)))

    print(f"\n{'agent':<11}{'case':<24}{'pass':<6}failed checks")
    for r in results:
        failed = [c["name"] for c in r["checks"] if not c["passed"]] or ([r["error"]] if r.get("error") else [])
        print(f"{r['agent']:<11}{r['case']:<24}{'yes' if r['passed'] else 'NO':<6}{', '.join(failed)}")
    by_agent: dict[str, list[bool]] = {}
    for r in results:
        by_agent.setdefault(r["agent"], []).append(r["passed"])
    print("\npass rate by agent:")
    for agent, passes in by_agent.items():
        print(f"  {agent:<11}{sum(passes)}/{len(passes)}")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{stamp}.json"
    out.write_text(json.dumps({"model": args.model or settings.agent_model, "results": results}, indent=2, default=str))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    asyncio.run(main())
