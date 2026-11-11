"""Per-agent graders: deterministic checks an agent's output must pass.

Each grader takes the case (brief + fixed upstream outputs) and the agent's output and returns
a list of named checks. They encode what "good" means for that role, so a prompt or model
change that breaks a role shows up as a failing check, not as a vague feeling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app import checks
from app.schemas import (
    ClientBrief,
    FactExtraction,
    IdentityDirections,
    IdentityOutput,
    MessagingOutput,
    QAOutput,
    ReportOutput,
    ResearchOutput,
    StrategyOutput,
)


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def _blockers(findings: list[checks.Finding]) -> list[checks.Finding]:
    return [f for f in findings if f.severity == "blocker"]


def grade_research(brief: ClientBrief, out: ResearchOutput, upstream: dict) -> list[Check]:
    covered = " ".join(c.name.lower() for c in out.competitor_landscape)
    missing = [c for c in brief.competitors if c.lower() not in covered]
    return [
        Check("3-6 audience insights", 3 <= len(out.audience_insights) <= 6, f"{len(out.audience_insights)} given"),
        Check("every insight has evidence", all(i.evidence.strip() for i in out.audience_insights)),
        Check("covers every named competitor", not missing, f"missing: {missing}" if missing else ""),
        Check("has regulatory notes", bool(out.regulatory_notes)),
        Check(
            "business profile filled and explained",
            bool(out.business_profile.business_type and out.business_profile.location and out.business_profile.basis),
        ),
        Check("1-6 clarifying questions", 1 <= len(out.open_questions) <= 6, f"{len(out.open_questions)} asked"),
        Check(
            "every question has a recommended answer",
            all(q.recommended_answer.strip() for q in out.open_questions),
        ),
    ]


def grade_strategy(brief: ClientBrief, out: StrategyOutput, upstream: dict) -> list[Check]:
    positioning = out.positioning_statement.lower()
    names_competitor = any(c.lower() in out.differentiation.lower() for c in brief.competitors)
    return [
        Check("3-5 pillars", 3 <= len(out.pillars) <= 5, f"{len(out.pillars)} pillars"),
        Check("every pillar has proof points", all(p.proof_points for p in out.pillars)),
        Check("positioning names the brand", brief.client_name.split()[0].lower() in positioning),
        Check("differentiation names a competitor", names_competitor or not brief.competitors),
        Check("lists risks", bool(out.risks)),
    ]


def grade_messaging(brief: ClientBrief, out: MessagingOutput, upstream: dict) -> list[Check]:
    strategy: StrategyOutput = upstream["strategy"]
    pillar_names = {p.name.lower() for p in strategy.pillars}
    covered = {m.pillar.lower() for m in out.key_messages}
    findings = checks.check_messaging(out, checks.is_alcohol_brand(brief.business_type))
    return [
        Check("3-5 taglines", 3 <= len(out.tagline_options) <= 5, f"{len(out.tagline_options)} taglines"),
        Check(
            "taglines are 8 words or fewer",
            all(len(t.split()) <= 8 for t in out.tagline_options),
        ),
        Check("key messages map to strategy pillars", covered <= pillar_names, f"unknown: {covered - pillar_names}"),
        Check("every pillar has a key message", pillar_names <= covered, f"uncovered: {pillar_names - covered}"),
        Check("copy for 3+ channels", len({c.channel for c in out.sample_copy}) >= 3),
        Check("tone has do's and don'ts", bool(out.tone_of_voice.do and out.tone_of_voice.dont)),
        Check("no compliance blockers", not _blockers(findings), "; ".join(f.problem for f in _blockers(findings))),
        Check(
            "no unsourced metrics",
            not [f for f in findings if "metric" in f.problem],
            "; ".join(f.problem for f in findings if "metric" in f.problem),
        ),
    ]


def grade_identity(brief: ClientBrief, out: IdentityOutput | IdentityDirections, upstream: dict) -> list[Check]:
    """One direction (the refiner), or the Identity Director's set of directions."""
    if isinstance(out, IdentityDirections):
        return grade_identity_directions(brief, out, upstream)
    findings = checks.check_identity(out)
    contrast = [f for f in findings if "contrast" in f.problem and "dark theme" not in f.problem]
    dark = [f for f in findings if f.location.startswith("identity.dark_tokens") and f.severity != "minor"]
    return [
        Check("valid hex everywhere", not [f for f in findings if "Invalid hex" in f.problem]),
        Check("3-7 palette colors", 3 <= len(out.color_palette) <= 7),
        Check("contrast minimums met", not contrast, "; ".join(f.problem for f in contrast)),
        Check("dark theme is dark and legible", not dark, "; ".join(f.problem for f in dark)),
        Check("accent is not a default AI indigo", out.tokens.accent.upper() not in checks.AI_DEFAULT_ACCENTS),
        Check("display and body faces differ", out.typography.display.lower() != out.typography.body.lower()),
        Check("states symbol logic", len(out.symbol_logic.split()) >= 5),
        Check("lists anti-patterns", bool(out.anti_patterns)),
    ]


def grade_identity_directions(brief: ClientBrief, out: IdentityDirections, upstream: dict) -> list[Check]:
    findings = checks.check_directions(out)
    accents = [d.tokens.accent.upper() for d in out.directions]
    methods = {d.logo_concept_method for d in out.directions}
    result = [
        Check("2-3 directions", 2 <= len(out.directions) <= 3, str(len(out.directions))),
        Check("recommendation is one of them", 0 <= out.recommended < len(out.directions)),
        Check("directions differ in accent", len(set(accents)) == len(accents)),
        Check("directions differ in logo method", len(methods) > 1),
        Check("explains the choice", len(out.comparison.split()) >= 15),
        Check("no blockers in any direction", not _blockers(findings), "; ".join(f.problem for f in _blockers(findings))),
    ]
    for i, direction in enumerate(out.directions):
        result += [
            Check(f"[{direction.direction_name or i}] {c.name}", c.passed, c.detail)
            for c in grade_identity(brief, direction, upstream)
        ]
    return result


def grade_report(brief: ClientBrief, out: ReportOutput, upstream: dict) -> list[Check]:
    findings = checks.check_report(out, checks.is_alcohol_brand(brief.business_type))
    headings = " ".join(s.heading.lower() for s in out.sections)
    missing = [t for t in checks.REQUIRED_REPORT_TOPICS if t not in headings]
    text = " ".join([out.executive_summary] + [s.body_markdown for s in out.sections])
    messaging: MessagingOutput = upstream["messaging"]
    uses_tagline = any(t.rstrip(".").lower() in text.lower() for t in messaging.tagline_options)
    return [
        Check("covers research/strategy/messaging/identity", not missing, f"missing: {missing}"),
        Check("executive summary <= 250 words", len(out.executive_summary.split()) <= 250),
        Check("has next steps", bool(out.next_steps)),
        Check("no placeholders or compliance blockers", not _blockers(findings), "; ".join(f.problem for f in _blockers(findings))),
        Check("quotes an approved tagline verbatim", uses_tagline),
    ]


def grade_qa(brief: ClientBrief, out: QAOutput, upstream: dict) -> list[Check]:
    """QA cases carry `expect_pass`: clean inputs must pass, planted defects must be caught."""
    expect_pass: bool = upstream["expect_pass"]
    gating = [i for i in out.issues if i.severity in ("blocker", "major")]
    result = [Check("verdict matches expectation", out.passed == expect_pass, f"passed={out.passed}")]
    if expect_pass:
        result.append(Check("no blocker/major issues on clean input", not gating, f"{len(gating)} raised"))
    else:
        planted: str = upstream["planted_location"]
        hit = [i for i in gating if i.location.lower().startswith(planted)]
        result.append(Check(f"flags the planted defect in {planted}", bool(hit)))
    result.append(Check("score in 1-10", 1 <= out.score <= 10, str(out.score)))
    return result


def grade_extractor(brief: ClientBrief, out: FactExtraction, upstream: dict, *, auto_save: float = 0.85) -> list[Check]:
    """Extractor cases carry `must_save` (substrings that must land >= auto_save) and
    `must_not_save` (substrings that must stay below it)."""
    saved = [f.statement.lower() for f in out.facts if f.confidence >= auto_save]
    result = []
    for needle in upstream["must_save"]:
        result.append(Check(f"auto-saves '{needle}'", any(needle.lower() in s for s in saved)))
    for needle in upstream["must_not_save"]:
        result.append(Check(f"does not auto-save '{needle}'", not any(needle.lower() in s for s in saved)))
    result.append(Check("confidences within 0-1", all(0 <= f.confidence <= 1 for f in out.facts)))
    result.append(Check("statements under 30 words", all(len(f.statement.split()) <= 30 for f in out.facts)))
    return result


GRADERS: dict[str, Callable[..., list[Check]]] = {
    "research": grade_research,
    "strategy": grade_strategy,
    "messaging": grade_messaging,
    "identity": grade_identity,
    "report": grade_report,
    "qa": grade_qa,
    "extractor": grade_extractor,
}
