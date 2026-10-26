"""Data shapes: the client brief, each agent's structured output, and run state.

Agent output models are sent to the model API as structured-output schemas, so
they keep to plain types with every field required (no defaults, no numeric
bounds). Range checks happen in code after parsing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- input


class ClientBrief(BaseModel):
    client_id: str = Field(description="Stable id for the client; brand facts are keyed on it.")
    client_name: str
    business_type: str = Field(description="e.g. craft brewery, plant-based bakery, coffee kiosk")
    location: str
    target_audience: str
    goals: list[str]
    constraints: list[str] = []
    competitors: list[str] = []
    products: list[str] = []
    notes: str = ""


# --------------------------------------------------------------------------- agent outputs


class AudienceInsight(BaseModel):
    insight: str
    evidence: str
    confidence: Literal["low", "medium", "high"]


class CompetitorNote(BaseModel):
    name: str
    positioning: str
    gap_we_can_own: str


class ClarifyingQuestion(BaseModel):
    question: str = Field(description="Worded so that answering 'yes' accepts the recommended answer.")
    why_it_matters: str
    recommended_answer: str


class ResearchOutput(BaseModel):
    market_summary: str
    audience_insights: list[AudienceInsight]
    competitor_landscape: list[CompetitorNote]
    category_trends: list[str]
    regulatory_notes: list[str] = Field(
        description="Labelling, health-claim, allergen or alcohol-marketing rules that apply."
    )
    open_questions: list[ClarifyingQuestion]


class BrandPillar(BaseModel):
    name: str
    description: str
    proof_points: list[str]


class StrategyOutput(BaseModel):
    positioning_statement: str
    brand_promise: str
    pillars: list[BrandPillar]
    personality_traits: list[str]
    differentiation: str
    risks: list[str]


class KeyMessage(BaseModel):
    pillar: str = Field(description="Name of the strategy pillar this message supports.")
    message: str
    proof: str


class ToneOfVoice(BaseModel):
    summary: str
    do: list[str]
    dont: list[str]


class CopySample(BaseModel):
    channel: str
    copy_text: str


class MessagingOutput(BaseModel):
    tagline_options: list[str]
    elevator_pitch: str
    key_messages: list[KeyMessage]
    tone_of_voice: ToneOfVoice
    sample_copy: list[CopySample]


class PaletteColor(BaseModel):
    name: str
    hex: str
    rationale: str


class Typography(BaseModel):
    display: str = Field(description="Typeface for headlines, menus boards, packaging names.")
    body: str = Field(description="Typeface for running text and UI.")
    rationale: str


class SemanticTokens(BaseModel):
    """Role-named colors (6-digit hex), the shape OpenDesign's tokens.css uses."""

    bg: str
    surface: str
    fg: str = Field(description="Body text color; needs 4.5:1 contrast on bg and surface.")
    muted: str = Field(description="Secondary text; needs 4.5:1 contrast on bg.")
    border: str
    accent: str = Field(description="The single brand accent.")
    accent_on: str = Field(description="Text color on accent fills; needs 4.5:1 contrast on accent.")
    success: str
    warn: str
    danger: str


LogoConceptMethod = Literal[
    "monogram_meaning", "product_action", "metaphor_fusion", "negative_space", "construction_geometry"
]


class IdentityOutput(BaseModel):
    visual_direction_summary: str
    mood_keywords: list[str]
    symbol_logic: str = Field(description="Core brand ideas and the symbols they map to.")
    color_palette: list[PaletteColor]
    tokens: SemanticTokens
    typography: Typography
    logo_concept_method: LogoConceptMethod
    logo_direction: str
    imagery_style: str
    packaging_and_signage_notes: str
    anti_patterns: list[str] = Field(description="Visual choices this brand must avoid, and why.")


class ReportSection(BaseModel):
    heading: str
    body_markdown: str


class ReportOutput(BaseModel):
    title: str
    executive_summary: str
    sections: list[ReportSection]
    next_steps: list[str]


class QAIssue(BaseModel):
    severity: Literal["blocker", "major", "minor"]
    location: str = Field(
        description="Deliverable and field, starting with research, strategy, messaging, identity or report "
        "(e.g. 'messaging.tagline_options', 'identity.tokens.accent', 'report.sections.Strategy')."
    )
    problem: str
    suggested_fix: str


class QAOutput(BaseModel):
    passed: bool
    score: int = Field(description="Overall quality from 1 (unusable) to 10 (client-ready).")
    issues: list[QAIssue]
    summary: str


FactCategory = Literal[
    "identity",  # name, location, founding story, ownership
    "product",  # menu, signature products, sourcing
    "audience",
    "positioning",  # approved positioning, promise, pillars
    "voice",  # approved tone rules
    "visual",  # approved colors, typography
    "constraint",  # budgets, must/must-not, legal
    "preference",  # stated likes/dislikes of the client
]


class ExtractedFact(BaseModel):
    category: FactCategory
    statement: str = Field(description="One self-contained, durable fact about the brand.")
    source: Literal["client_brief", "client_answer", "human_feedback", "approved_output"]
    evidence: str = Field(description="Short quote or pointer to where this was stated.")
    confidence: float = Field(description="0.0-1.0: how certain it is this is true and durable.")


class FactExtraction(BaseModel):
    facts: list[ExtractedFact]


# --------------------------------------------------------------------------- memory


class FactStatus(str, Enum):
    active = "active"
    pending = "pending"
    rejected = "rejected"


class ClientSummary(BaseModel):
    id: str
    name: str
    active_facts: int
    pending_facts: int


class BrandFact(BaseModel):
    id: int | None = None
    client_id: str
    category: str
    statement: str
    source: str
    evidence: str
    confidence: float
    status: FactStatus
    source_run_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- run state


class Stage(str, Enum):
    research = "research"
    strategy = "strategy"
    creative = "creative"  # Messaging Lead + Identity Direction, in parallel
    report = "report"  # Report Producer + QA Reviewer loop
    final = "final"  # human sign-off, then fact extraction
    done = "done"


STAGE_ORDER = [Stage.research, Stage.strategy, Stage.creative, Stage.report, Stage.final]


class RunStatus(str, Enum):
    running = "running"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    rejected = "rejected"
    failed = "failed"


class Decision(str, Enum):
    approve = "approve"
    request_changes = "request_changes"
    reject = "reject"


class RunEvent(BaseModel):
    at: datetime = Field(default_factory=utcnow)
    kind: str
    stage: str | None = None
    actor: str = "system"
    detail: dict[str, Any] = {}


class ClientAnswer(BaseModel):
    question: str
    answer: str


class Run(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    brief: ClientBrief
    stage: Stage = Stage.research
    status: RunStatus = RunStatus.running
    outputs: dict[str, dict[str, Any]] = {}
    feedback: dict[str, list[str]] = {}
    # Answers to the Research Analyst's clarifying questions, given at the research checkpoint.
    answers: list[ClientAnswer] = []
    qa_attempts: int = 0
    qa_escalated: bool = False
    error: str | None = None
    usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    @property
    def client_id(self) -> str:
        return self.brief.client_id
