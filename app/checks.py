"""Deterministic checks that do not need a model.

The QA Reviewer runs these before its own review and a blocker here fails QA
regardless of what the model says. The evaluation suite reuses them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.schemas import IdentityOutput, MessagingOutput, ReportOutput

Severity = Literal["blocker", "major", "minor"]


@dataclass(frozen=True)
class Finding:
    severity: Severity
    location: str
    problem: str


# Health / medical claims that food and drink brands cannot make without
# authorisation (FDA, EU 1924/2006, FSANZ). Kept deliberately narrow so it does
# not fire on ordinary copy like "a treat" or "fresh".
_HEALTH_CLAIM_PATTERNS = [
    r"\bcures?\b",
    r"\bheals?\b",
    r"\bclinically[- ]proven\b",
    r"\bboosts? (your )?immun(e|ity)\b",
    r"\bdetox(ify|ifies|ifying)?\b",
    r"\bprevents? (disease|cancer|illness|diabetes)\b",
    r"\bburns? fat\b",
    r"\bweight[- ]loss\b",
    r"\btreats? (anxiety|depression|inflammation|disease)\b",
]

# Alcohol marketing must not appeal to minors or tie drinking to performance.
_ALCOHOL_PATTERNS = [
    r"\b(for )?kids\b",
    r"\bchildren\b",
    r"\bteens?\b",
    r"\bdrink (more|up) to\b",
    r"\bmakes? you (stronger|smarter|more attractive)\b",
]

_PLACEHOLDER_PATTERNS = [
    r"lorem ipsum",
    r"\[(tbd|todo|insert[^\]]*|client name|placeholder)\]",
    r"\{\{?\s*\w+\s*\}?\}",
    r"\bTODO\b",
    r"\bXXX\b",
]

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

ALCOHOL_KEYWORDS = ("brew", "beer", "wine", "winery", "distill", "spirits", "cider", "cocktail", "bar\\b", "pub\\b", "taproom")


def _scan(text: str, patterns: list[str]) -> list[str]:
    hits = []
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            hits.append(match.group(0))
    return hits


def health_claims(text: str, location: str) -> list[Finding]:
    return [
        Finding("blocker", location, f"Unauthorised health/medical claim: '{hit}'")
        for hit in _scan(text, _HEALTH_CLAIM_PATTERNS)
    ]


def alcohol_marketing(text: str, location: str) -> list[Finding]:
    return [
        Finding("blocker", location, f"Alcohol copy that may appeal to minors or imply benefit: '{hit}'")
        for hit in _scan(text, _ALCOHOL_PATTERNS)
    ]


def placeholders(text: str, location: str) -> list[Finding]:
    return [
        Finding("blocker", location, f"Unfilled placeholder text: '{hit}'")
        for hit in _scan(text, _PLACEHOLDER_PATTERNS)
    ]


def is_alcohol_brand(business_type: str) -> bool:
    return any(re.search(rf"\b{k}", business_type, flags=re.IGNORECASE) for k in ALCOHOL_KEYWORDS)


def check_messaging(messaging: MessagingOutput, alcohol: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    if not 3 <= len(messaging.tagline_options) <= 5:
        findings.append(
            Finding("major", "messaging.tagline_options", "Expected 3-5 tagline options")
        )
    for tagline in messaging.tagline_options:
        if len(tagline.split()) > 8:
            findings.append(
                Finding("minor", "messaging.tagline_options", f"Tagline over 8 words: '{tagline}'")
            )
    text = " ".join(
        [*messaging.tagline_options, messaging.elevator_pitch]
        + [m.message for m in messaging.key_messages]
        + [c.copy_text for c in messaging.sample_copy]
    )
    findings += health_claims(text, "messaging")
    findings += invented_metrics(text, "messaging")
    if alcohol:
        findings += alcohol_marketing(text, "messaging")
    return findings


# Craft rules adapted from OpenDesign's craft/color.md and craft/anti-ai-slop.md
# (github.com/nexu-io/open-design, Apache-2.0; originally from refero_skill, MIT).

# Tailwind indigo/violet defaults: the most common "an AI picked this" accent.
AI_DEFAULT_ACCENTS = {"#6366F1", "#4F46E5", "#4338CA", "#3730A3", "#8B5CF6", "#7C3AED", "#A855F7"}

# Invented performance metrics ("10x", "99.9%", "#1 in town") with no source.
_INVENTED_METRIC_PATTERNS = [
    r"\b\d+(\.\d+)?\s?[x×]\s(faster|better|more|fresher)\b",
    r"\b\d{2,3}(\.\d+)?%\s(of|satisfaction|happier|customers|guests|fresher|natural)\b",
    r"#1\b",
    r"\bnumber one\b",
    r"\baward[- ]winning\b",
]


def invented_metrics(text: str, location: str) -> list[Finding]:
    return [
        Finding("major", location, f"Unsourced metric or award claim: '{hit}'")
        for hit in _scan(text, _INVENTED_METRIC_PATTERNS)
    ]


def _luminance(hex_color: str) -> float:
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast_ratio(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio between two #RRGGBB colors."""
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (foreground token, background token, minimum ratio, severity if below)
CONTRAST_PAIRS = [
    ("fg", "bg", 4.5, "blocker"),
    ("fg", "surface", 4.5, "blocker"),
    ("muted", "bg", 4.5, "major"),
    ("accent_on", "accent", 4.5, "major"),
    ("accent", "bg", 3.0, "major"),
]


def check_identity(identity: IdentityOutput) -> list[Finding]:
    findings: list[Finding] = []
    if not 3 <= len(identity.color_palette) <= 7:
        findings.append(Finding("major", "identity.color_palette", "Expected 3-7 palette colors"))
    for color in identity.color_palette:
        if not _HEX.match(color.hex):
            findings.append(
                Finding("blocker", "identity.color_palette", f"Invalid hex '{color.hex}' for {color.name}")
            )
    hexes = [c.hex.upper() for c in identity.color_palette]
    if len(set(hexes)) != len(hexes):
        findings.append(Finding("minor", "identity.color_palette", "Duplicate colors in palette"))

    tokens = identity.tokens.model_dump()
    bad_tokens = [name for name, value in tokens.items() if not _HEX.match(value)]
    for name in bad_tokens:
        findings.append(Finding("blocker", f"identity.tokens.{name}", f"Invalid hex '{tokens[name]}'"))
    if bad_tokens:
        return findings

    for fg, bg, minimum, severity in CONTRAST_PAIRS:
        ratio = contrast_ratio(tokens[fg], tokens[bg])
        if ratio < minimum:
            findings.append(
                Finding(
                    severity,
                    f"identity.tokens.{fg}",
                    f"{fg} on {bg} contrast is {ratio:.2f}:1, below the {minimum}:1 minimum",
                )
            )
    if tokens["accent"].upper() in AI_DEFAULT_ACCENTS:
        findings.append(
            Finding("major", "identity.tokens.accent", "Accent is a default Tailwind indigo/violet; pick an ownable color")
        )
    for name in ("bg", "fg"):
        if tokens[name].upper() in ("#000000", "#FFFFFF"):
            findings.append(
                Finding("minor", f"identity.tokens.{name}", "Pure black/white causes glare; use an off-shade")
            )
    return findings


REQUIRED_REPORT_TOPICS = ("research", "strategy", "messaging", "identity")


def check_report(report: ReportOutput, alcohol: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    headings = " ".join(s.heading.lower() for s in report.sections)
    for topic in REQUIRED_REPORT_TOPICS:
        if topic not in headings:
            findings.append(Finding("major", "report.sections", f"No section covering {topic}"))
    if len(report.executive_summary.split()) > 250:
        findings.append(Finding("minor", "report.executive_summary", "Executive summary over 250 words"))
    if not report.next_steps:
        findings.append(Finding("major", "report.next_steps", "No next steps"))
    text = "\n".join(
        [report.title, report.executive_summary]
        + [s.body_markdown for s in report.sections]
        + report.next_steps
    )
    findings += placeholders(text, "report")
    findings += health_claims(text, "report")
    findings += invented_metrics(text, "report")
    if alcohol:
        findings += alcohol_marketing(text, "report")
    return findings
