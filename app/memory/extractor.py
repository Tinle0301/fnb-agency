"""Fact extraction: a smaller model pulls durable brand facts out of a finished session.

Each fact comes back with a confidence score, and the score decides what happens:

    confidence >= auto_save_threshold  -> stored as an active brand fact
    review_threshold <= c < auto_save  -> stored as pending, waiting for a human
    confidence < review_threshold      -> dropped

Only human-approved deliverables, human feedback and the client brief are shown to
the extractor. Setting APPROVED_OUTPUT_CONFIDENCE_CAP below the auto-save threshold
additionally routes every fact worded by an agent through human review once.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.base import Agent, AgentContext, as_json, render_client
from app.logging_setup import get_logger
from app.schemas import BrandFact, ExtractedFact, FactExtraction, FactStatus

log = get_logger(__name__)


class FactExtractor(Agent[FactExtraction]):
    name = "fact_extractor"
    role = """Fact Extractor. You read a finished branding engagement and pull out the facts \
about this client that will still be true in the next engagement, so the agency never has to \
ask again.

Extract a fact only if it is durable and specific: business identity and history, products and \
sourcing, the target audience, the human-approved positioning, voice rules and visual choices, \
hard constraints, and preferences the client or strategist stated. Do not extract opinions about \
the market, speculation, rejected ideas, or anything the human feedback overruled.

Confidence (0.0-1.0) means: how sure are you that this is true AND will stay true?
- 0.9-1.0: stated plainly by the client brief, a client answer, or human feedback.
- 0.7-0.89: contained in a deliverable a human approved, or clearly implied by the brief.
- 0.4-0.69: inferred, partly supported, or might change soon.
- below 0.4: guesswork; usually leave it out instead.
Keep each statement self-contained (name the brand) and under 30 words. Do not repeat facts \
already listed under brand_facts."""
    output_type = FactExtraction

    def build_prompt(self, ctx: AgentContext) -> str:
        parts = [render_client(ctx)]
        feedback = ctx.extra.get("human_feedback", [])
        parts.append(f"<human_feedback>\n{as_json(feedback)}\n</human_feedback>")
        approved = ctx.extra.get("approved_outputs", {})
        parts.append(f"<approved_deliverables>\n{as_json(approved)}\n</approved_deliverables>")
        return "\n\n".join(parts) + "\n\nExtract the durable brand facts."


@dataclass
class TriageResult:
    active: list[BrandFact] = field(default_factory=list)
    pending: list[BrandFact] = field(default_factory=list)
    dropped: list[ExtractedFact] = field(default_factory=list)

    @property
    def to_save(self) -> list[BrandFact]:
        return self.active + self.pending


def triage_facts(
    extracted: list[ExtractedFact],
    *,
    client_id: str,
    run_id: str,
    auto_save_threshold: float,
    review_threshold: float,
    approved_output_cap: float | None = None,
) -> TriageResult:
    """Sort extracted facts into active / pending / dropped by confidence."""
    result = TriageResult()
    for fact in extracted:
        confidence = min(max(fact.confidence, 0.0), 1.0)
        if not fact.statement.strip():
            result.dropped.append(fact)
            continue
        # Approved deliverables were signed off by a person, but the wording is the model's.
        # Optionally keep them below auto-save so a human confirms them once.
        if approved_output_cap is not None and fact.source == "approved_output":
            confidence = min(confidence, approved_output_cap)

        if confidence >= auto_save_threshold:
            status = FactStatus.active
        elif confidence >= review_threshold:
            status = FactStatus.pending
        else:
            result.dropped.append(fact)
            log.info(
                "fact.dropped",
                statement=fact.statement,
                confidence=confidence,
                source=fact.source,
            )
            continue

        brand_fact = BrandFact(
            client_id=client_id,
            category=fact.category,
            statement=fact.statement.strip(),
            source=fact.source,
            evidence=fact.evidence,
            confidence=round(confidence, 3),
            status=status,
            source_run_id=run_id,
        )
        (result.active if status is FactStatus.active else result.pending).append(brand_fact)
    return result
