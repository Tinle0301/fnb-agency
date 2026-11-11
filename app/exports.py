"""Deliverable exports: the client report as Markdown, and the identity as a design system.

The design system follows OpenDesign's portable package layout
(github.com/nexu-io/open-design, `design-systems/<slug>/`):

    manifest.json   schemaVersion od-design-system-project/v1
    DESIGN.md       design prose agents read when building the client's website
    tokens.css      role-named CSS custom properties

so the approved identity can be dropped into OpenDesign (or handed to any coding agent) and
the client's site is built against the brand the client signed off on.

The zip also carries BRAND_GUIDELINE.md: a production guideline for making the visual assets
(logo set, social, print, menu, packaging). It is written so a human designer can work from it
as a brief, and so each section can be pasted into an AI design tool (Lovart, Midjourney,
Firefly, Canva and the like) with the same brand rules every time.

And SEO_BRIEF.md: the search starter kit for whoever builds the site. Local keywords, a title
and meta description per page from the approved messaging, Schema.org JSON-LD for the business
(placeholders where the brief has no data), a Google Business Profile checklist and a build
checklist. It is generated in code from the approved work, so it costs no model calls.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from urllib.parse import urlparse

from app.checks import CONTRAST_PAIRS, contrast_ratio
from app.schemas import (
    ClientBrief,
    IdentityOutput,
    MessagingOutput,
    ReportOutput,
    SemanticTokens,
    StrategyOutput,
    ResearchOutput,
)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "brand"


def report_markdown(report: ReportOutput, research: ResearchOutput | None = None) -> str:
    parts = [f"# {report.title}", "", "## Executive summary", "", report.executive_summary, ""]
    for section in report.sections:
        parts += [f"## {section.heading}", "", section.body_markdown.strip(), ""]
    if research is not None:
        parts += research_tables_md(research)
    parts += ["## Next steps", ""] + [f"- {step}" for step in report.next_steps]
    return "\n".join(parts).strip() + "\n"


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|") or "–"


def _source(url: str) -> str:
    if not url.startswith(("https://", "http://")):
        return "no source"
    host = re.sub(r"^www\.", "", urlparse(url).netloc) or url
    return f"[{_cell(host)}]({url.replace(')', '%29').replace(' ', '%20')})"


PRESENCE_STATUS = {"found": "Found", "not_found": "Not found", "unverified": "Not confirmed"}


def research_tables_md(research: ResearchOutput) -> list[str]:
    """Research's data as Markdown tables, one source link per row (generated in code, not by a model)."""
    out = ["## Market data and sources", ""]
    if research.market_facts:
        out += ["| What | Finding | Source |", "|---|---|---|"]
        out += [f"| {_cell(f.topic)} | {_cell(f.value)} | {_source(f.source_url)} |" for f in research.market_facts]
        out.append("")
    if research.online_presence:
        out += ["### Online presence", "", "| Channel | Status | Details | Source |", "|---|---|---|---|"]
        out += [
            f"| {_cell(p.channel)} | {PRESENCE_STATUS.get(p.status, p.status)} | {_cell(p.detail)} | {_source(p.source_url)} |"
            for p in research.online_presence
        ]
        out.append("")
    if research.competitor_landscape:
        out += ["### Competitors", "", "| Competitor | Where | Positioning | Gap we can own | Source |", "|---|---|---|---|---|"]
        out += [
            f"| {_cell(c.name)} | {_cell(c.where)} | {_cell(c.positioning)} | {_cell(c.gap_we_can_own)} | {_source(c.source_url)} |"
            for c in research.competitor_landscape
        ]
        out.append("")
    return out


def design_md(
    brief: ClientBrief, strategy: StrategyOutput, messaging: MessagingOutput, identity: IdentityOutput
) -> str:
    t, d = identity.tokens, identity.dark_tokens
    palette = "\n".join(f"- **{c.name}:** `{c.hex}` — {c.rationale}" for c in identity.color_palette)
    do = "\n".join(f"- {d}" for d in messaging.tone_of_voice.do)
    dont = "\n".join(f"- {d}" for d in messaging.tone_of_voice.dont)
    anti = "\n".join(f"- {a}" for a in identity.anti_patterns)
    mood = ", ".join(identity.mood_keywords)
    return f"""# {brief.client_name} Design System

> Category: Food & Beverage
> {strategy.positioning_statement}

## 1. Visual Theme & Atmosphere

**Direction: {identity.direction_name}.** {identity.visual_direction_summary}

- **Mood:** {mood}
- **Symbol logic:** {identity.symbol_logic}
- **Imagery:** {identity.imagery_style}

## 2. Color

{palette}

Role tokens (see `tokens.css`):

- Background `{t.bg}`, surface `{t.surface}`, text `{t.fg}`, muted text `{t.muted}`, border `{t.border}`.
- Accent `{t.accent}` with `{t.accent_on}` text on it. Use the accent for at most two elements per screen, typically the primary call to action and one highlight.
- Semantic: success `{t.success}`, warning `{t.warn}`, danger `{t.danger}`; reserve these for states, never decoration.

Dark theme (dark menus, night signage, dark mode; `tokens.css` switches on `prefers-color-scheme: dark` or `data-theme="dark"`):

- Background `{d.bg}`, surface `{d.surface}`, text `{d.fg}`, muted text `{d.muted}`, border `{d.border}`.
- Accent `{d.accent}` with `{d.accent_on}` text on it. Semantic: success `{d.success}`, warning `{d.warn}`, danger `{d.danger}`.

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


def _color_vars(t: SemanticTokens, indent: str = "  ") -> str:
    pairs = [
        ("bg", t.bg), ("surface", t.surface), ("fg", t.fg), ("muted", t.muted), ("border", t.border),
        ("accent", t.accent), ("accent-on", t.accent_on), ("success", t.success), ("warn", t.warn),
        ("danger", t.danger),
    ]
    return "\n".join(f"{indent}--{name}: {value};" for name, value in pairs)


def tokens_css(brief: ClientBrief, identity: IdentityOutput) -> str:
    return f"""/* tokens.css for {brief.client_name}. Generated from the approved identity direction
   ("{identity.direction_name}"). Light theme by default; the dark theme follows the visitor's
   system setting, and data-theme="light" or "dark" on <html> forces one. */

:root {{
{_color_vars(identity.tokens)}
  --accent-hover: color-mix(in oklab, var(--accent), black 8%);
  --accent-active: color-mix(in oklab, var(--accent), black 14%);
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
  color-scheme: light;
}}

@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
{_color_vars(identity.dark_tokens, "    ")}
    --accent-hover: color-mix(in oklab, var(--accent), white 10%);
    --accent-active: color-mix(in oklab, var(--accent), white 16%);
    color-scheme: dark;
  }}
}}

:root[data-theme="dark"] {{
{_color_vars(identity.dark_tokens)}
  --accent-hover: color-mix(in oklab, var(--accent), white 10%);
  --accent-active: color-mix(in oklab, var(--accent), white 16%);
  color-scheme: dark;
}}
"""


# The starter asset kit: (asset, size/format, what it must show). Every asset uses the same
# brand block, so whoever makes them (a designer or an AI design tool) stays on-brand.
ASSET_KIT = [
    ("Logo set", "SVG + PNG; primary, stacked, mark-only; full color, one-color dark, one-color light",
     "The primary logo plus a mark-only version that still reads at 32px (favicon) and 15mm (stamp)."),
    ("Social profile image", "1080 x 1080 px; keep the mark inside the central circle, since platforms crop to one",
     "The mark alone on the brand background, no tagline."),
    ("Instagram post template", "1080 x 1350 px, 4:5",
     "A reusable layout: product photo area, headline in the display face, small logo, one accent element."),
    ("Instagram story template", "1080 x 1920 px, 9:16; keep 250 px at the top and bottom free of text",
     "Full-bleed photo, short headline, one call to action."),
    ("Business card", "85 x 55 mm, plus 3 mm bleed, CMYK print file",
     "Front: logo on the brand color. Back: name, role, address, opening hours, website."),
    ("Menu page", "A4 or A3 portrait, print and PDF",
     "Section titles in the display face, items and prices in the body face, allergen marks as text."),
    ("Packaging or label", "To the printer's dieline",
     "Product name in the display face; leave a clear panel for allergens, legal and barcode."),
    ("Brand guideline sheet", "One page, A4 landscape",
     "Logo versions, palette with hex codes, the two typefaces, three example images, do's and don'ts."),
]


def _contrast_rows(t: SemanticTokens) -> str:
    values = t.model_dump()
    rows = []
    for fg, bg, minimum, _ in CONTRAST_PAIRS:
        ratio = contrast_ratio(values[fg], values[bg])
        verdict = "pass" if ratio >= minimum else "FAIL"
        rows.append(f"| {fg} on {bg} | `{values[fg]}` on `{values[bg]}` | {ratio:.1f}:1 | {minimum}:1 | {verdict} |")
    return "\n".join(rows)


def _token_table(t: SemanticTokens) -> str:
    labels = {
        "bg": "Background", "surface": "Cards and panels", "fg": "Text", "muted": "Secondary text",
        "border": "Lines and dividers", "accent": "Brand accent (buttons, highlights)",
        "accent_on": "Text on the accent", "success": "Success state", "warn": "Warning state",
        "danger": "Error state",
    }
    return "\n".join(f"| {labels[k]} | `{v}` |" for k, v in t.model_dump().items())


def _asset_prompt(client_name: str, name: str, size: str, what: str, tagline: str) -> str:
    noun = name if name.startswith("Instagram") else name[0].lower() + name[1:]
    text = f"Using the brand block above, create the {noun} for {client_name}. Size and format: {size}. {what}"
    if name == "Logo set":
        text += " Show every version on the light and the dark background."
    text += " Keep it legible, simple and consistent with the rest of the kit."
    if name.startswith("Instagram") and tagline:
        text += f' Headline, if the layout needs one: "{tagline}"'
    return f"**{name}**\n\n```text\n{text}\n```"


def brand_brief_block(
    brief: ClientBrief, strategy: StrategyOutput, messaging: MessagingOutput, identity: IdentityOutput
) -> str:
    """The brand block every prompt starts with: the same facts and rules for every asset."""
    palette = ", ".join(f"{c.name} {c.hex}" for c in identity.color_palette)
    traits = ", ".join(strategy.personality_traits)
    avoid = "; ".join(identity.anti_patterns)
    return (
        f"Brand: {brief.client_name}, a {brief.business_type} in {brief.location}.\n"
        f"Audience: {brief.target_audience}.\n"
        f"Positioning: {strategy.positioning_statement}\n"
        f"Personality: {traits}.\n"
        f"Visual direction \"{identity.direction_name}\": {identity.visual_direction_summary} "
        f"Mood: {', '.join(identity.mood_keywords)}.\n"
        f"Logo idea: {identity.logo_direction}\n"
        f"Colors (use only these): {palette}. Light background {identity.tokens.bg}, text {identity.tokens.fg}, "
        f"accent {identity.tokens.accent}. Dark background {identity.dark_tokens.bg}, text {identity.dark_tokens.fg}, "
        f"accent {identity.dark_tokens.accent}.\n"
        f"Fonts: {identity.typography.display} for headings, {identity.typography.body} for body text.\n"
        f"Photography and graphics: {identity.imagery_style}\n"
        f"Avoid: {avoid}; generic stock symbols; gradients, glows and effects that will date; "
        f"health or nutrition claims; tiny or decorative text for prices and allergens."
    )


def brand_guideline_md(
    brief: ClientBrief, strategy: StrategyOutput, messaging: MessagingOutput, identity: IdentityOutput
) -> str:
    """Production guideline for a designer or an AI design tool, built from the approved work."""
    block = brand_brief_block(brief, strategy, messaging, identity)
    lead_tagline = messaging.tagline_options[0] if messaging.tagline_options else ""
    palette_rows = "\n".join(f"| {c.name} | `{c.hex}` | {c.rationale} |" for c in identity.color_palette)
    pillars = "\n".join(f"- **{p.name}:** {p.description}" for p in strategy.pillars)
    do = "\n".join(f"- {x}" for x in messaging.tone_of_voice.do)
    dont = "\n".join(f"- {x}" for x in messaging.tone_of_voice.dont)
    samples = "\n".join(f"- **{c.channel}:** {c.copy_text}" for c in messaging.sample_copy)
    avoid = "\n".join(f"- {a}" for a in identity.anti_patterns)
    asset_rows = "\n".join(f"| {name} | {size} | {what} |" for name, size, what in ASSET_KIT)
    asset_prompts = "\n\n".join(
        _asset_prompt(brief.client_name, name, size, what, lead_tagline) for name, size, what in ASSET_KIT
    )
    return f"""# {brief.client_name}: Brand Production Guideline

Direction: **{identity.direction_name}**. Use this guide to make the logo and the starter visuals, whether a designer
makes them or an AI design tool does. Everything here comes from the agency's strategy, messaging and identity work;
use the copy downloaded after final sign-off for production, and ask before changing anything it sets.

## How to use this guide

**Designer:** treat sections 1 to 6 as the brief and section 7 as the deliverables list. Work up two or three logo
sketches inside the stated concept, then refine one. Hand back source files plus the checks in section 9.

**AI design tool** (Lovart, Midjourney, Firefly, Canva or similar):

1. If the tool has a brand kit, save the palette hex codes, the two typefaces and the approved logo there first.
2. Paste the brand block (section 8) at the start of the conversation, then the prompt for each asset.
3. Ask for three options per asset, pick one, then ask for refinements: simplify, fix spacing, check it on dark.
4. Treat every output as a draft. Run the checks in section 9 before anything is published.

## 1. Brand at a glance

- **Business:** {brief.business_type}, {brief.location}
- **For:** {brief.target_audience}
- **Positioning:** {strategy.positioning_statement}
- **Promise:** {strategy.brand_promise}
- **Personality:** {", ".join(strategy.personality_traits)}
- **Taglines:** {" / ".join(messaging.tagline_options)}

Pillars:

{pillars}

## 2. Logo

- **Concept method:** {identity.logo_concept_method.replace("_", " ")}
- **Idea:** {identity.logo_direction}
- **Symbol logic:** {identity.symbol_logic}

Rules: simple enough to read at 32px and as a 15mm stamp; works in one color on both the light and dark background;
no generic food icons (chef hats, forks, leaves, steam swirls) unless the concept above calls for one; distinct from
{", ".join(brief.competitors) if brief.competitors else "competitors in the area"}.

Versions to deliver: primary, stacked, mark only; full color, one-color dark, one-color light.

## 3. Color

| Name | Hex | Why |
|---|---|---|
{palette_rows}

Light theme (default):

| Role | Hex |
|---|---|
{_token_table(identity.tokens)}

Dark theme (dark menus, night signage, dark mode):

| Role | Hex |
|---|---|
{_token_table(identity.dark_tokens)}

Use the accent sparingly: one main action or highlight per layout. Semantic colors are for states, never decoration.

Contrast, light theme:

| Pair | Colors | Ratio | Minimum | Result |
|---|---|---|---|---|
{_contrast_rows(identity.tokens)}

Contrast, dark theme:

| Pair | Colors | Ratio | Minimum | Result |
|---|---|---|---|---|
{_contrast_rows(identity.dark_tokens)}

## 4. Typography

- **Headings:** {identity.typography.display}
- **Body, menus, prices, small print:** {identity.typography.body}
- {identity.typography.rationale}

Use only these two. Body text at least 9pt in print and 16px on screen; never set prices, allergens or legal text in
the display face. Confirm the license covers web, print and packaging before use.

## 5. Photography and graphics

{identity.imagery_style}

Mood: {", ".join(identity.mood_keywords)}.

## 6. Voice

{messaging.tone_of_voice.summary}

Do:
{do}

Don't:
{dont}

Sample copy:
{samples}

Avoid visually:
{avoid}

## 7. Starter asset kit

| Asset | Size / format | Must show |
|---|---|---|
{asset_rows}

Packaging and signage notes: {identity.packaging_and_signage_notes}

## 8. Prompts for AI design tools

Paste this brand block first, once per conversation or project:

```text
{block}
```

Master prompt (three directions within the approved identity, to start the logo work):

```text
Using the brand block above, create the visual identity for {brief.client_name} in the "{identity.direction_name}"
direction. Develop 3 logo options using the concept above, each simple and memorable. For the strongest, show the
logo on the light and the dark background, the palette with hex codes, the heading and body fonts, and an example
photo style. Show the identity on a social profile image, an Instagram post and a business card. Keep everything
legible, cohesive and practical. Avoid generic symbols, unnecessary effects and complicated logo details. Present the
options side by side so I can compare and refine them.
```

Asset prompts:

{asset_prompts}

## 9. Before anything is published

- [ ] Spelling of the name, tagline, address and prices
- [ ] Logo reads at 32px and as a 15mm stamp, in one color, on light and dark
- [ ] Text contrast meets the minimums in section 3 (check exported files, not just the source)
- [ ] Fonts are licensed for web, print and packaging
- [ ] The logo and visuals are clearly different from {", ".join(brief.competitors) if brief.competitors else "competitors"} and from well-known brands
- [ ] Only palette colors are used; one accent per layout
- [ ] No health, medical or nutrition claims; allergen and legal panels have room
- [ ] AI output reviewed by a person; the final choices are made by the client and the agency
"""


# Schema.org type per kind of F&B business. First keyword found in the business type wins.
SCHEMA_TYPES = [
    ("brewery", "Brewery"), ("brewpub", "Brewery"), ("winery", "Winery"), ("distillery", "Distillery"),
    ("bakery", "Bakery"), ("patisserie", "Bakery"), ("coffee", "CafeOrCoffeeShop"), ("cafe", "CafeOrCoffeeShop"),
    ("café", "CafeOrCoffeeShop"), ("tea", "CafeOrCoffeeShop"), ("ice cream", "IceCreamShop"),
    ("gelato", "IceCreamShop"), ("bar", "BarOrPub"), ("pub", "BarOrPub"), ("fast food", "FastFoodRestaurant"),
    ("restaurant", "Restaurant"), ("bistro", "Restaurant"), ("kitchen", "Restaurant"), ("grill", "Restaurant"),
    ("steakhouse", "Restaurant"), ("pizzeria", "Restaurant"), ("barbecue", "Restaurant"), ("bbq", "Restaurant"),
    ("diner", "Restaurant"), ("eatery", "Restaurant"),
]
ALCOHOL_TYPES = {"Brewery", "Winery", "Distillery", "BarOrPub"}
META_LIMIT = 155
TITLE_LIMIT = 60


def schema_type(business_type: str) -> str:
    text = business_type.lower()
    for keyword, kind in SCHEMA_TYPES:
        if re.search(rf"\b{re.escape(keyword)}(s|es)?\b", text):
            return kind
    return "FoodEstablishment"


def _city(location: str) -> str:
    return location.split(",")[0].strip() or location


def _clip(text: str, limit: int) -> str:
    """Shorten to the limit at a word boundary, so drafts fit search result snippets."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut + "…"


def _title(*parts: str) -> str:
    """Join title parts with ' | ', dropping trailing parts until it fits."""
    kept = [p for p in parts if p]
    while len(kept) > 1 and len(" | ".join(kept)) > TITLE_LIMIT:
        kept.pop()
    return _clip(" | ".join(kept), TITLE_LIMIT)


def _main_kind(business_type: str) -> str:
    """'craft brewery and taproom' -> 'craft brewery': the phrase people actually search."""
    return re.split(r",| and | & | with ", business_type.lower())[0].strip() or business_type.lower()


def local_keywords(brief: ClientBrief) -> list[str]:
    city, kind = _city(brief.location), _main_kind(brief.business_type)
    words = [
        f"{kind} {city}",
        f"{kind} near me",
        f"best {kind} in {city}",
        f"{brief.client_name} {city}",
    ]
    words += [f"{p} {city}" for p in brief.products[:5]]
    seen: set[str] = set()
    return [w for w in words if not (w.lower() in seen or seen.add(w.lower()))]


def page_plan(brief: ClientBrief, strategy: StrategyOutput, messaging: MessagingOutput) -> list[tuple[str, str, str, str]]:
    """(page, path, title, meta description) for the starter site."""
    name, city, kind = brief.client_name, _city(brief.location), brief.business_type
    products = ", ".join(brief.products[:3])
    tagline = messaging.tagline_options[0] if messaging.tagline_options else ""
    story = messaging.key_messages[0].message if messaging.key_messages else strategy.brand_promise
    menu_meta = f"See what's on at {name}" + (f": {products} and more." if products else ".") + f" {kind.capitalize()} in {city}."
    return [
        ("Home", "/", _title(name, f"{kind.capitalize()} in {city}", tagline), _clip(messaging.elevator_pitch, META_LIMIT)),
        ("Menu", "/menu", _title(f"Menu", name, city), _clip(menu_meta, META_LIMIT)),
        ("Our story", "/about", _title(f"Our story", name), _clip(f"{story} {strategy.brand_promise}", META_LIMIT)),
        ("Visit", "/visit", _title(f"Visit us in {city}", name),
         _clip(f"Find {name} in {brief.location}. Opening hours, address, directions and parking.", META_LIMIT)),
        ("Contact", "/contact", _title("Contact", name),
         _clip(f"Get in touch with {name} in {city} for bookings, events and wholesale.", META_LIMIT)),
    ]


def business_json_ld(brief: ClientBrief, messaging: MessagingOutput) -> dict:
    """Schema.org markup for the business. Values in CAPITALS are placeholders the builder fills."""
    kind = schema_type(brief.business_type)
    data = {
        "@context": "https://schema.org",
        "@type": kind,
        "name": brief.client_name,
        "description": _clip(messaging.elevator_pitch, 300),
        "url": "https://EXAMPLE.COM/",
        "logo": "https://EXAMPLE.COM/logo.png",
        "image": ["https://EXAMPLE.COM/photos/storefront.jpg"],
        "telephone": "PHONE NUMBER",
        "priceRange": "$$",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "STREET ADDRESS",
            "addressLocality": _city(brief.location),
            "addressRegion": brief.location.split(",")[1].strip() if "," in brief.location else "REGION",
            "postalCode": "POSTCODE",
            "addressCountry": "COUNTRY CODE",
        },
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
             "opens": "HH:MM", "closes": "HH:MM"},
            {"@type": "OpeningHoursSpecification", "dayOfWeek": ["Saturday", "Sunday"], "opens": "HH:MM", "closes": "HH:MM"},
        ],
        "hasMenu": "https://EXAMPLE.COM/menu",
        "sameAs": ["INSTAGRAM URL", "GOOGLE BUSINESS PROFILE URL"],
    }
    return data


def menu_json_ld(brief: ClientBrief) -> dict:
    items = [
        {"@type": "MenuItem", "name": p, "description": "ONE-LINE DESCRIPTION",
         "offers": {"@type": "Offer", "price": "0.00", "priceCurrency": "CURRENCY"}}
        for p in brief.products
    ] or [{"@type": "MenuItem", "name": "ITEM NAME", "description": "ONE-LINE DESCRIPTION"}]
    return {
        "@context": "https://schema.org",
        "@type": "Menu",
        "name": f"{brief.client_name} menu",
        "hasMenuSection": [{"@type": "MenuSection", "name": "SECTION NAME", "hasMenuItem": items}],
    }


def seo_brief_md(
    brief: ClientBrief, strategy: StrategyOutput, messaging: MessagingOutput, identity: IdentityOutput
) -> str:
    """Search starter kit for the person or tool building the client's site."""
    kind = schema_type(brief.business_type)
    city = _city(brief.location)
    keywords = "\n".join(f"- {k}" for k in local_keywords(brief))
    pages = "\n".join(
        f"| {page} | `{path}` | {title.replace('|', chr(92) + '|')} ({len(title)}) | {meta} ({len(meta)}) |"
        for page, path, title, meta in page_plan(brief, strategy, messaging)
    )
    business = json.dumps(business_json_ld(brief, messaging), indent=2, ensure_ascii=False)
    menu = json.dumps(menu_json_ld(brief), indent=2, ensure_ascii=False)
    gbp_description = _clip(f"{messaging.elevator_pitch} {strategy.brand_promise}", 750)
    posts = "\n".join(f"  - {c.copy_text}" for c in messaging.sample_copy[:3])
    alcohol = (
        "\n- [ ] Alcohol: follow the local rules on age gates and responsible-drinking wording, and never aim "
        "pages or ads at people under the legal drinking age."
        if kind in ALCOHOL_TYPES else ""
    )
    competitors = ", ".join(brief.competitors) if brief.competitors else "the nearest competitors"
    return f"""# {brief.client_name}: SEO Starter Brief

For the person or tool building the website. It turns the approved brand into the basics a local
{brief.business_type} needs to be found on Google, Google Maps and AI search answers. Values in CAPITALS are
placeholders: fill them with the client's real details before launch. Copy drafts follow the approved voice; keep the
facts, adjust the wording to fit the page.

## 1. What people search for

Start with these local searches. Check volumes in Google Keyword Planner or Search Console once the site is live,
and add the phrases the client hears from guests.

{keywords}

Rules: one main search phrase per page; use it in the title, the H1 and the first paragraph, written naturally.
Never stuff keywords or city names into the business name, on the site or on the Google Business Profile.

## 2. Pages, titles and meta descriptions

Titles stay under {TITLE_LIMIT} characters and meta descriptions under {META_LIMIT}; the number in brackets is the
current length.

| Page | Path | Title | Meta description |
|---|---|---|---|
{pages}

Every page gets one H1, a `lang` attribute, a canonical URL and an Open Graph image (1200 x 630 px, brand
background `{identity.tokens.bg}`, logo and one photo).

## 3. Structured data (JSON-LD)

Put this in the `<head>` of every page, with the placeholders filled. Schema.org type: **{kind}**. If the business
takes bookings, add `"acceptsReservations": true`.

```json
{business}
```

On the menu page, add the menu as well (one section per menu heading):

```json
{menu}
```

Test both with Google's Rich Results Test and the Schema.org validator before launch. Do not add star ratings or
reviews about the business to its own markup: Google ignores self-served reviews for local businesses.

## 4. Google Business Profile

- [ ] Claim and verify the profile. Primary category matches what the business is ({brief.business_type}).
- [ ] Name exactly as on the sign: **{brief.client_name}**, no extra keywords.
- [ ] Name, address and phone identical on the site footer, the profile, Instagram and every directory listing.
- [ ] Opening hours, including holiday hours, kept current. Menu link points to `/menu`.
- [ ] At least 10 photos in the approved style: {identity.imagery_style}
- [ ] Logo (mark-only version) as the profile image, a cover photo of the space or the signature product.
- [ ] Reply to every review within a few days, in the brand voice: {messaging.tone_of_voice.summary}
- [ ] Post weekly. Starters from the approved copy:
{posts}

Business description (up to 750 characters):

```text
{gbp_description}
```

## 5. Build checklist

- [ ] The menu is HTML text on the page, not only a PDF or an image, with prices and allergen labels as text.
- [ ] Address, opening hours and phone number in text in the footer of every page, phone as a `tel:` link.
- [ ] An embedded map and a directions link on `/visit`.
- [ ] Every image has alt text that says what it shows; file names are descriptive (`{slugify(brief.client_name)}-storefront.jpg`, not `IMG_1234.jpg`).
- [ ] Hero image compressed (WebP or AVIF), with width and height set; it loads in under 2.5 s on a phone.
- [ ] Works on a phone first: tap targets at least 44 px, no text smaller than 16 px.
- [ ] `sitemap.xml` and `robots.txt` in place; the site verified in Google Search Console and the sitemap submitted.
- [ ] Favicon from the mark-only logo (32 px and 180 px).
- [ ] A short FAQ on the visit page (parking, dogs, kids, accessibility, bookings): it answers what guests ask and
      gives AI search tools clear facts to quote.
- [ ] No health, medical or nutrition claims in page copy, titles or markup.{alcohol}

## 6. After launch

- Run a technical and local SEO audit on the live site and fix what it finds.
- Check in Search Console after four weeks: which searches show the site, and which pages get clicks.
- Compare the Google Maps listing with {competitors} for {brief.business_type} searches in {city}: photos, review
  count and reply rate are where a new listing catches up fastest.
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
        "BRAND_GUIDELINE.md": brand_guideline_md(brief, strategy, messaging, identity),
        "SEO_BRIEF.md": seo_brief_md(brief, strategy, messaging, identity),
    }


def design_system_zip(files: dict[str, str], slug: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(f"{slug}/{name}", content)
    return buffer.getvalue()
