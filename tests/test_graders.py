"""Every grader passes the golden outputs and catches a planted defect.

This is the offline half of the per-agent evaluations: it proves the graders can tell good
from bad before they are trusted to score live model output (`python -m evals.run`).
"""

from __future__ import annotations

import pytest

from evals import fixtures as fx
from evals.graders import GRADERS
from evals.run import build_cases

B = fx.BREWERY_BRIEF


def failed(checks):
    return [c.name for c in checks if not c.passed]


GOLDEN = [
    ("research", fx.BREWERY_RESEARCH, {}),
    ("strategy", fx.BREWERY_STRATEGY, {}),
    ("messaging", fx.BREWERY_MESSAGING, {"strategy": fx.BREWERY_STRATEGY}),
    ("identity", fx.BREWERY_IDENTITY, {}),
    ("report", fx.BREWERY_REPORT, {"messaging": fx.BREWERY_MESSAGING}),
    ("qa", fx.QA_PASS, {"expect_pass": True}),
    ("qa", fx.QA_FAIL, {"expect_pass": False, "planted_location": "messaging"}),
]


@pytest.mark.parametrize("agent,output,upstream", GOLDEN, ids=[f"{a}-{i}" for i, (a, *_ ) in enumerate(GOLDEN)])
def test_golden_output_passes(agent, output, upstream):
    assert failed(GRADERS[agent](B, output, upstream)) == []


def test_research_missing_competitor_fails():
    out = fx.BREWERY_RESEARCH.model_copy(update={"competitor_landscape": fx.BREWERY_RESEARCH.competitor_landscape[:1]})
    assert "covers every named competitor" in failed(GRADERS["research"](B, out, {}))


def test_research_without_questions_fails():
    out = fx.BREWERY_RESEARCH.model_copy(update={"open_questions": []})
    assert "1-6 clarifying questions" in failed(GRADERS["research"](B, out, {}))


def test_strategy_pillar_without_proof_fails():
    pillars = [p.model_copy(update={"proof_points": []}) for p in fx.BREWERY_STRATEGY.pillars]
    out = fx.BREWERY_STRATEGY.model_copy(update={"pillars": pillars})
    assert "every pillar has proof points" in failed(GRADERS["strategy"](B, out, {}))


@pytest.mark.parametrize(
    "tagline,check",
    [
        ("Clinically proven to relax you.", "no compliance blockers"),
        ("Voted #1 in Maine.", "no unsourced metrics"),
        ("A beer brewed slowly by the sea for people who love the coast", "taglines are 8 words or fewer"),
        ("Perfect for teens after school.", "no compliance blockers"),
    ],
)
def test_messaging_defects_fail(tagline, check):
    out = fx.BREWERY_MESSAGING.model_copy(update={"tagline_options": [tagline, *fx.BREWERY_MESSAGING.tagline_options[1:]]})
    assert check in failed(GRADERS["messaging"](B, out, {"strategy": fx.BREWERY_STRATEGY}))


def test_messaging_off_strategy_pillar_fails():
    msgs = [m.model_copy(update={"pillar": "Rock and Roll"}) for m in fx.BREWERY_MESSAGING.key_messages]
    out = fx.BREWERY_MESSAGING.model_copy(update={"key_messages": msgs})
    result = failed(GRADERS["messaging"](B, out, {"strategy": fx.BREWERY_STRATEGY}))
    assert "key messages map to strategy pillars" in result


@pytest.mark.parametrize(
    "tokens,check",
    [
        ({"muted": "#B9B2A6"}, "contrast minimums met"),
        ({"accent": "#6366F1", "accent_on": "#FFFFFF"}, "accent is not a default AI indigo"),
        ({"fg": "1C2321"}, "valid hex everywhere"),
    ],
)
def test_identity_defects_fail(tokens, check):
    out = fx.BREWERY_IDENTITY.model_copy(update={"tokens": fx.BREWERY_IDENTITY.tokens.model_copy(update=tokens)})
    assert check in failed(GRADERS["identity"](B, out, {}))


def test_report_with_placeholder_fails():
    sections = [*fx.BREWERY_REPORT.sections[:-1], fx.BREWERY_REPORT.sections[-1].model_copy(update={"body_markdown": "[TBD]"})]
    out = fx.BREWERY_REPORT.model_copy(update={"sections": sections})
    assert "no placeholders or compliance blockers" in failed(GRADERS["report"](B, out, {"messaging": fx.BREWERY_MESSAGING}))


def test_qa_that_passes_a_planted_defect_fails():
    upstream = {"expect_pass": False, "planted_location": "messaging"}
    assert "verdict matches expectation" in failed(GRADERS["qa"](B, fx.QA_PASS, upstream))


def test_extractor_grader_catches_speculation_saved_as_fact():
    upstream = {"must_save": ["lobstermen"], "must_not_save": ["boston"]}
    assert failed(GRADERS["extractor"](B, fx.BREWERY_FACTS, upstream)) == []
    boosted = fx.BREWERY_FACTS.model_copy(
        update={"facts": [f.model_copy(update={"confidence": 0.9}) for f in fx.BREWERY_FACTS.facts]}
    )
    assert "does not auto-save 'boston'" in failed(GRADERS["extractor"](B, boosted, upstream))


def test_every_agent_has_live_eval_cases():
    assert {c.agent for c in build_cases()} == set(GRADERS)
