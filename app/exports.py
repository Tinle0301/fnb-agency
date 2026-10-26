"""Deliverable exports: the client report as Markdown, and the identity as a design system.

The design system follows OpenDesign's portable package layout
(github.com/nexu-io/open-design, `design-systems/<slug>/`):

    manifest.json   schemaVersion od-design-system-project/v1
    DESIGN.md       design prose agents read when building the client's website
    tokens.css      role-named CSS custom properties

so the approved identity can be dropped into OpenDesign (or handed to any coding agent) and
the client's site is built against the brand the client signed off on.
"""

from __future__ import annotations

import io
import json
import re
import zipfile

from app.schemas import (
    ClientBrief,
    IdentityOutput,
    MessagingOutput,
    ReportOutput,
    StrategyOutput,
)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "brand"


def report_markdown(report: ReportOutput) -> str:
    parts = [f"# {report.title}", "", "## Executive summary", "", report.executive_summary, ""]
    for section in report.sections:
        parts += [f"## {section.heading}", "", section.body_markdown.strip(), ""]
    parts += ["## Next steps", ""] + [f"- {step}" for step in report.next_steps]
    return "\n".join(parts).strip() + "\n"


def design_md(
    brief: ClientBrief, strategy: StrategyOutput, messaging: MessagingOutput, identity: IdentityOutput
) -> str:
    t = identity.tokens
    palette = "\n".join(f"- **{c.name}:** `{c.hex}` — {c.rationale}" for c in identity.color_palette)
    do = "\n".join(f"- {d}" for d in messaging.tone_of_voice.do)
    dont = "\n".join(f"- {d}" for d in messaging.tone_of_voice.dont)
    anti = "\n".join(f"- {a}" for a in identity.anti_patterns)
    mood = ", ".join(identity.mood_keywords)
    return f"""# {brief.client_name} Design System

> Category: Food & Beverage
> {strategy.positioning_statement}

## 1. Visual Theme & Atmosphere

{identity.visual_direction_summary}

- **Mood:** {mood}
- **Symbol logic:** {identity.symbol_logic}
- **Imagery:** {identity.imagery_style}

## 2. Color

{palette}

Role tokens (see `tokens.css`):

- Background `{t.bg}`, surface `{t.surface}`, text `{t.fg}`, muted text `{t.muted}`, border `{t.border}`.
- Accent `{t.accent}` with `{t.accent_on}` text on it. Use the accent for at most two elements per screen, typically the primary call to action and one highlight.
- Semantic: success `{t.success}`, warning `{t.warn}`, danger `{t.danger}`; reserve these for states, never decoration.

## 3. Typography

- **Display:** {identity.typography.display} (headlines, menu section titles, product names)
- **Body:** {identity.typography.body} (running text, menus, UI)
- {identity.typography.rationale}

## 4. Spacing & Grid

- Spacing scale: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64.
- Menus and price lists align to a strict column grid so items and prices scan in one pass.

## 5. Layout & Composition

- Lead with the product and the place: food, drink and space photography carries the page before any feature list.
- Keep hierarchy obvious: headline, one line of support copy, one action (order, book, visit).
- Opening hours, address and allergen information are always one tap away.

## 6. Components

- Primary button: accent fill `{t.accent}`, label `{t.accent_on}`; secondary buttons stay neutral.
- Menu items: name in the display face, description in body, price right-aligned, dietary and allergen marks as text labels, not color alone.
- Cards: consistent radius and spacing; separate with whitespace before borders or shadows.

## 7. Motion & Interaction

- Short, calm transitions (150–250ms). Hover, focus-visible, active, disabled and loading states are explicit.

## 8. Voice & Brand

{messaging.tone_of_voice.summary}

**Taglines:** {" / ".join(messaging.tagline_options)}

Do:
{do}

Don't:
{dont}

**Logo:** {identity.logo_direction}

**Packaging & signage:** {identity.packaging_and_signage_notes}

## 9. Anti-patterns

{anti}
- No health, medical or nutrition claims in copy or imagery captions.
- No off-palette colors where a token already solves the problem.
"""


def tokens_css(brief: ClientBrief, identity: IdentityOutput) -> str:
    t = identity.tokens
    return f"""/* tokens.css for {brief.client_name}. Generated from the approved identity direction. */

:root {{
  --bg: {t.bg};
  --surface: {t.surface};
  --fg: {t.fg};
  --muted: {t.muted};
  --border: {t.border};
  --accent: {t.accent};
  --accent-on: {t.accent_on};
  --accent-hover: color-mix(in oklab, var(--accent), black 8%);
  --accent-active: color-mix(in oklab, var(--accent), black 14%);
  --success: {t.success};
  --warn: {t.warn};
  --danger: {t.danger};
  --font-display: "{identity.typography.display}", Georgia, serif;
  --font-body: "{identity.typography.body}", system-ui, sans-serif;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;
  --space-16: 64px;
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-pill: 9999px;
  --motion-fast: 150ms;
  --motion-base: 240ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
}}
"""


def manifest_json(brief: ClientBrief, strategy: StrategyOutput) -> str:
    manifest = {
        "schemaVersion": "od-design-system-project/v1",
        "id": slugify(brief.client_name),
        "name": brief.client_name,
        "category": "Food & Beverage",
        "description": strategy.positioning_statement[:240],
        "source": {"type": "bundled", "origin": "F&B virtual agency (approved identity direction)"},
        "files": {"design": "DESIGN.md", "tokens": "tokens.css"},
        "craft": {"applies": [], "suggested": ["color", "accessibility-baseline"], "exemptions": []},
    }
    return json.dumps(manifest, indent=2) + "\n"


def design_system_files(
    brief: ClientBrief, strategy: StrategyOutput, messaging: MessagingOutput, identity: IdentityOutput
) -> dict[str, str]:
    return {
        "manifest.json": manifest_json(brief, strategy),
        "DESIGN.md": design_md(brief, strategy, messaging, identity),
        "tokens.css": tokens_css(brief, identity),
    }


def design_system_zip(files: dict[str, str], slug: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(f"{slug}/{name}", content)
    return buffer.getvalue()
