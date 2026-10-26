"""Shared agent machinery: context passed between agents, prompt helpers, timed runs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel

from app.llm import LLM, LLMResult
from app.logging_setup import get_logger, log_context
from app.schemas import BrandFact, ClientAnswer, ClientBrief
from app.untrusted import FLAGGED_NOTE, UNTRUSTED_NOTE, flag_instruction_like

T = TypeVar("T", bound=BaseModel)
log = get_logger(__name__)

AGENCY_PREAMBLE = """You are part of a small brand agency team that works only with food and \
beverage businesses (restaurants, cafés, bakeries, breweries, packaged goods). Your work is \
reviewed by a QA reviewer and a human strategist before any client sees it.

Ground rules for every deliverable:
- Build on the client brief and the stored brand facts. Stored facts were confirmed in earlier \
engagements; do not contradict them unless the brief explicitly changes them.
- State only what you can trace to the brief, the client's answers, the brand facts or the \
approved deliverables, and say so when you are inferring or do not know. Statistics, awards, \
certifications, sourcing claims, customers, testimonials and quotes appear only when a source \
states them.
- Food and drink copy must not make health, medical, or nutrition claims (e.g. "boosts immunity", \
"detox", "cures") and alcohol brands must not market to minors or tie drinking to success.
- If reviewer or human feedback is included, address every point of it."""


@dataclass
class AgentContext:
    brief: ClientBrief
    facts: list[BrandFact] = field(default_factory=list)
    answers: list[ClientAnswer] = field(default_factory=list)
    outputs: dict[str, BaseModel] = field(default_factory=dict)
    feedback: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


def as_json(model: BaseModel | dict | list) -> str:
    if isinstance(model, BaseModel):
        return model.model_dump_json(indent=2)
    return json.dumps(model, indent=2, default=str)


def _untrusted_block(tag: str, body: str) -> str:
    flagged = flag_instruction_like(body)
    if flagged:
        log.warning("untrusted.instruction_like", block=tag, lines=flagged)
    note = UNTRUSTED_NOTE
    if flagged:
        note += f" {FLAGGED_NOTE}\ninstruction_like: {json.dumps(flagged)}"
    return f"<{tag}>\n<note>{note}</note>\n{body}\n</{tag}>"


def render_brief(brief: ClientBrief) -> str:
    return _untrusted_block("client_brief", as_json(brief))


def render_facts(facts: list[BrandFact]) -> str:
    if not facts:
        return "<brand_facts>\nNo stored facts yet; this is a new client.\n</brand_facts>"
    lines = [f"- [{f.category}] {f.statement}" for f in facts]
    return "<brand_facts>\n" + "\n".join(lines) + "\n</brand_facts>"


def render_answers(answers: list[ClientAnswer]) -> str:
    if not answers:
        return ""
    lines = "\n".join(f"- Q: {a.question}\n  A: {a.answer}" for a in answers)
    return "\n\n" + _untrusted_block("client_answers", f"The client answered these clarifying questions:\n{lines}")


def render_client(ctx: "AgentContext") -> str:
    """Brief, the client's answers to clarifying questions, and stored brand facts."""
    return f"{render_brief(ctx.brief)}{render_answers(ctx.answers)}\n\n{render_facts(ctx.facts)}"


def render_output(name: str, output: BaseModel) -> str:
    return f"<{name}>\n{as_json(output)}\n</{name}>"


def render_feedback(feedback: list[str]) -> str:
    if not feedback:
        return ""
    items = "\n".join(f"- {f}" for f in feedback)
    return (
        "\n<revision_feedback>\nA previous draft of this deliverable was sent back. "
        f"Address each point:\n{items}\n</revision_feedback>"
    )


@dataclass
class AgentResult(Generic[T]):
    agent: str
    output: T
    llm: LLMResult[T]
    latency_ms: int


class Agent(Generic[T]):
    """One specialist. Subclasses set name/role/output_type and write build_prompt."""

    name: ClassVar[str]
    role: ClassVar[str]
    output_type: ClassVar[type[BaseModel]]

    def __init__(self, llm: LLM, model: str, effort: str | None = None) -> None:
        self.llm = llm
        self.model = model
        self.effort = effort

    @property
    def system_prompt(self) -> str:
        return f"{AGENCY_PREAMBLE}\n\nYour role: {self.role}"

    def build_prompt(self, ctx: AgentContext) -> str:
        raise NotImplementedError

    async def run(self, ctx: AgentContext) -> AgentResult[T]:
        prompt = self.build_prompt(ctx)
        with log_context(agent=self.name):
            log.info("agent.started", model=self.model, prompt_chars=len(prompt), revision=bool(ctx.feedback))
            started = time.perf_counter()
            try:
                result = await self.llm.generate(
                    system=self.system_prompt,
                    prompt=prompt,
                    output_type=self.output_type,
                    model=self.model,
                    effort=self.effort,
                )
            except Exception as exc:
                log.error(
                    "agent.failed",
                    exc_info=True,
                    error=str(exc),
                    latency_ms=int((time.perf_counter() - started) * 1000),
                )
                raise
            latency_ms = int((time.perf_counter() - started) * 1000)
            log.info(
                "agent.completed",
                latency_ms=latency_ms,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                served_model=result.model,
            )
        return AgentResult(agent=self.name, output=result.output, llm=result, latency_ms=latency_ms)
