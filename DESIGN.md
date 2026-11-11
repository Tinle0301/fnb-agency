---
version: alpha
name: F&B Agency Dashboard
description: Working dashboard where a person steers six specialist agents from client brief to signed-off brand. Warm paper ground, coffee-brown signal, near-black shell, serif display over a system sans. Values without a PROPOSED comment are in app/static/dashboard.html today.
colors:
  # Neutrals
  bg: "#f3f1ec"              # --bg, page ground
  panel: "#ffffff"           # --panel, cards, inputs, tables
  ink: "#17150f"             # --ink, primary text
  ink-muted: "#6a655c"       # --ink2, secondary text (5.1:1 on bg)
  line: "#e6e2d8"            # --line, borders and rules
  zebra: "#faf9f6"           # --zebra, even table rows
  tag: "#eceae4"             # neutral pill / step badge fill (raw hex today)
  tag-ink: "#5c5346"         # text on tag (raw hex today, 6.3:1)
  # Shell (header, nav, table heads, primary buttons)
  shell: "#14130f"           # --navy (despite the name, a warm near-black)
  shell-raised: "#241f17"    # header gradient start (raw hex today)
  shell-hover: "#2b261d"     # primary button hover (raw hex today)
  shell-line: "#2c281f"      # nav bottom border (raw hex today)
  shell-ink: "#ffffff"
  shell-ink-muted: "#c8c2b6" # header subtitle (10.5:1 on shell)
  shell-nav: "#ada695"       # inactive nav link (7.7:1 on shell)
  # Brand
  brand: "#9C6B3F"           # --brand, coffee brown: the signal for "waiting for you"
  brand-light: "#bb8350"     # --brand2, on dark shell and as focus ring (3.2:1 on white)
  brand-soft: "#f4ece2"      # --brand-soft, waiting-state wash
  brand-ink: "#8a5d36"       # PROPOSED: brand-coloured small text on bg/brand-soft (5.0:1 / 4.9:1)
  focus: "#bb8350"           # PROPOSED alias of brand-light for every :focus-visible ring
  # Semantic: fill, soft background, ink for text on the soft background
  success: "#2f9e6b"         # --g
  success-soft: "#e2f3ea"    # --g-soft
  success-ink: "#23744f"     # PROPOSED (4.9:1 on success-soft; current text is 2.9:1)
  warning: "#b5851f"         # --a
  warning-soft: "#faf0d8"    # --a-soft
  warning-ink: "#7d5c12"     # PROPOSED (5.4:1 on warning-soft; current text is 2.9:1)
  danger: "#d8593f"          # --r
  danger-soft: "#f7e1da"     # --r-soft
  danger-ink: "#a83f2a"      # PROPOSED (4.9:1 on danger-soft; current text is 3.1:1)
  info: "#3d6f8e"            # --i
  info-soft: "#e1ecf3"       # --i-soft
  info-ink: "#336079"        # PROPOSED (5.7:1 on info-soft; current text is 4.5:1, borderline)
typography:
  display-title:
    fontFamily: Georgia, "Times New Roman", serif
    fontSize: 30px
    fontWeight: 800
    letterSpacing: 0.5px
  section-title:
    fontFamily: Georgia, "Times New Roman", serif
    fontSize: 23px
    fontWeight: 700
  figure-lg:
    fontFamily: Georgia, "Times New Roman", serif
    fontSize: 34px
    fontWeight: 800
    lineHeight: 1.15
    fontFeature: '"tnum"'      # PROPOSED: tabular figures on KPI numbers
  quote:
    fontFamily: Georgia, "Times New Roman", serif
    fontSize: 17px
    lineHeight: 1.45
  heading-sm:
    fontFamily: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial, sans-serif
    fontSize: 14.5px
    fontWeight: 700
  body:
    fontFamily: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial, sans-serif
    fontSize: 14px
    lineHeight: 1.5
  body-prose:
    fontFamily: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial, sans-serif
    fontSize: 15px              # PROPOSED: report and research prose (today 12.5-14px)
    lineHeight: 1.6
  small:
    fontFamily: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial, sans-serif
    fontSize: 12.5px
    lineHeight: 1.45
  label:
    fontFamily: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial, sans-serif
    fontSize: 12px              # PROPOSED: today 10-11px, uppercase, tracked 0.4-3.5px
    fontWeight: 700
  control:
    fontFamily: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Arial, sans-serif
    fontSize: 12.5px
    fontWeight: 700
rounded:
  sm: 6px      # step badge
  md: 10px     # PROPOSED single control/tile radius (today 8px, 9px and 10px are all used)
  lg: 12px     # cards
  pill: 20px   # pills, chips, nav counts
spacing:       # PROPOSED scale; today's values range 4-26px in 1px steps. Matches the client export's --space-* scale.
  1: 4px
  2: 8px
  3: 12px
  4: 16px
  6: 24px
  8: 32px
  12: 48px
  16: 64px
components:
  button:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.md}"
    padding: 8px 14px
  button-hover:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
  button-primary:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.shell-ink}"
    typography: "{typography.control}"
    rounded: "{rounded.md}"
    padding: 8px 14px
  button-primary-hover:
    backgroundColor: "{colors.shell-hover}"
    textColor: "{colors.shell-ink}"
  input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 9px 11px
  card:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.lg}"
    padding: 16px 17px
  pill:
    backgroundColor: "{colors.tag}"
    textColor: "{colors.tag-ink}"
    rounded: "{rounded.pill}"
    padding: 2px 9px
  pill-success:
    backgroundColor: "{colors.success-soft}"
    textColor: "{colors.success-ink}"
  pill-warning:
    backgroundColor: "{colors.warning-soft}"
    textColor: "{colors.warning-ink}"
  pill-danger:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger-ink}"
  pill-info:
    backgroundColor: "{colors.info-soft}"
    textColor: "{colors.info-ink}"
  tab-active:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.shell-ink}"
    rounded: "{rounded.md}"
  nav-bar:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.shell-nav}"
    height: 44px
  nav-link-active:
    textColor: "{colors.shell-ink}"
  table-header:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.shell-ink}"
    padding: 9px
  banner-waiting:
    backgroundColor: "{colors.brand-soft}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    padding: 11px 14px
  step-waiting:
    backgroundColor: "{colors.brand-soft}"
    textColor: "{colors.brand-ink}"
    rounded: "{rounded.md}"
    padding: 8px 10px
  toast:
    backgroundColor: "{colors.shell}"
    textColor: "{colors.shell-ink}"
    rounded: "{rounded.md}"
    padding: 10px 16px
---

## Overview

The agency dashboard is an **Operate** surface: one person reviews engagements, answers the client's questions, and approves or sends back work at three checkpoints. Its job is to make "what needs me now" obvious and every agent's output easy to read and judge. Brand lives in precise details, never in decoration.

The look descends from the Rề Cà Phê brand dashboard: a warm paper ground, white working surfaces, a near-black shell (header, sticky nav, table heads, primary actions) and a single coffee-brown signal that always means *a person is needed here*. A serif display face gives page titles and big figures a printed, considered voice; everything you read or operate is a plain system sans.

This file describes the dashboard only. Each client's website follows the `DESIGN.md` inside that client's design-system export, never this one.

The signature element is the **engagement pipeline**: one step per agent and per checkpoint, coloured by state. Spend detail there before anywhere else.

## Colors

The palette is mostly neutral (paper, white, warm ink) with one brand signal and four semantic states. CSS variable names in `dashboard.html` are in brackets.

- **Paper (`#f3f1ec`, `--bg`):** the page ground. Warmer than white so white cards read as surfaces without shadows.
- **Panel (`#ffffff`, `--panel`):** cards, inputs, tables, steps.
- **Ink (`#17150f`, `--ink`) and muted ink (`#6a655c`, `--ink2`):** primary and secondary text. Muted ink passes 4.5:1 on paper and panel.
- **Line (`#e6e2d8`, `--line`):** 1px borders and rules. Decorative only (1.3:1); never the only edge of an input that must be found.
- **Shell (`#14130f`, `--navy`):** header, nav, table heads, primary buttons, active tabs, toasts. The variable is called navy but the colour is a warm near-black; keep the hue warm.
- **Brand (`#9C6B3F`, `--brand`):** the "waiting for you" signal: the open checkpoint, the hot KPI, link colour, the waiting banner edge. Use it only where a person is needed or for the current selection. It passes 4.5:1 on white (4.6:1) but not on paper (4.05:1), so brand-coloured *small text on paper* uses **brand-ink (`#8a5d36`, PROPOSED)**.
- **Brand light (`#bb8350`, `--brand2`):** the brand on dark shell surfaces (nav underline, count badges, header kicker) and the focus ring (3.2:1 on white, passes the 3:1 non-text minimum).
- **Brand soft (`#f4ece2`, `--brand-soft`):** wash behind the waiting step and banner.
- **Semantic states:** success green (`--g`), warning amber (`--a`), danger red (`--r`), info blue (`--i`), each with a soft background. Today the state colour is also used as text on its soft background, which fails contrast (2.9–3.1:1 for green, amber and red). The PROPOSED `-ink` tokens fix this while keeping the fill colours for dots, badges and borders. Info is used for "working"; success for done and approved; danger for failed and rejected; warning for QA issues.

Pipeline state colours: done = success, working = info, waiting for you = brand, failed = danger, skipped = 45% opacity.

## Typography

Two families. **Georgia** (system serif) is the display voice: the dashboard title, section titles, KPI figures, block quotes and taglines. A **system sans stack** carries everything else. The dashboard is a private tool with no external requests, so system faces are deliberate here. PROPOSED, optional: self-host one display serif with more character as a `woff2` under `app/static/` if the dashboard is ever shown to clients.

Scale in use: 30px title, 23px section title, 34px KPI figure, 17px quote, 14.5px small heading, 14px body, 12.5px small text and controls, 10–11px labels. The scale has too many near-identical sizes (11, 11.5, 12, 12.5, 12.8, 13, 13.5px all appear). PROPOSED: collapse to 12 / 12.5 / 14 / 15 / 17 / 23 / 30 / 34 and raise every label to at least 12px.

Labels (`label.f`, KPI labels, lane headings, `.dnum`) are uppercase and letter-spaced today. PROPOSED for new work: sentence case, untracked, `label` token weight 700 in `ink-muted` or `brand-ink`. Report and research prose should move to `body-prose` (15px, 1.6) for comfortable reading. KPI figures and counts use tabular numerals.

## Layout

- **Container:** max 1300px, centred, 24px gutters (16px under 640px).
- **Breakpoints:** 960px (two-column layouts, lanes and the engagement sidebar stack; KPIs go 2-up) and 640px (forms single-column, title shrinks to 24px).
- **Grids:** KPIs 4-up; Overview lanes 3-up; engagement page main column + 330px sidebar; brief form 2-up with wide fields spanning; mini-cards `auto-fill, minmax(230px, 1fr)`.
- **Spacing:** use the spacing scale above (PROPOSED; the same 4–64px scale the client export already ships). Today's values (7, 9, 11, 13, 15, 17, 26px…) should snap to the nearest step when touched.
- **Density:** controls about 34px tall, tables at 12.5px. Show every lane's header and first cards on a 1440×900 screen.

## Elevation & Depth

Depth comes from tone, not shadow: white panels on warm paper.

- **Cards and run cards:** `0 1px 2px rgba(16,24,40,.05)` plus a 1px `line` border. PROPOSED: drop the shadow on in-flow cards (border or shadow, not both) and keep shadows only for things that float.
- **Floating:** the toast and any future menu or dialog take a real shadow, PROPOSED `0 8px 24px rgba(20,19,15,.18)`.
- **Sticky nav:** `rgba(20,19,15,.97)` with `backdrop-filter: blur(8px)` over scrolling content. The one sanctioned blur.
- **Header:** `linear-gradient(115deg, #241f17, #14130f)`, a two-stop tonal gradient within the shell hue, used only here.
- **Z-order:** nav 60, toast 90. PROPOSED scale for new layers: dropdown 100, sticky 200, dialog 400, toast 500.

## Shapes

- Cards 12px; run cards, steps, tables, banners, frames 10px; buttons and inputs 9px; header note 8px; step badge 6px; pills and chips 20px.
- PROPOSED: collapse 8/9/10px into a single `md` 10px. Keep radii concentric when nesting (inner = outer − padding).
- Status is never shown by shape alone.

## Components

- **Buttons:** white with a `line` border, `ink` text, 12.5px bold; hover turns the border brand. **Primary** is shell with white text, hover `#2b261d`. **Danger** keeps the default button with danger-coloured text. Disabled: 50% opacity, `not-allowed` cursor (PROPOSED: 0.55 and the native attribute always set, which the code already does). PROPOSED additions: `:active` scale 0.97 over 120ms; a designed `:focus-visible` ring in `focus`; a loading state that keeps width.
- **Inputs and textareas:** white, 1px `line` border, 9px radius, `focus` outline 2px inset on focus. Labels above in the `label` style; hints in muted ink.
- **Cards** (`.card`): white, 12px radius, 16–17px padding.
- **Run cards** (`.runcard`): Overview engagement tiles with a state colour bar along the top, client name, meta line and status pills; whole card is a link.
- **Pills** (`.pill`): 10.5px bold, 20px radius; variants ok / warn / bad / info / accent. Text must use the `-ink` tokens (PROPOSED).
- **Pipeline steps** (`.step`): white tiles with a numbered 24px badge, title and state line. Checkpoint steps are dashed and narrower. States: done (success badge), run (info border, pulsing badge), wait (2px brand border on brand-soft), fail (danger), skip (45% opacity).
- **Banner** (`.banner`): full-width status strip at the top of an engagement: waiting, failed, done, info; carries the one action for that state (Retry stage, etc.).
- **Tabs** (`.tabs`): row of buttons; the active one becomes shell-filled.
- **Nav bar:** sticky shell bar, 12.5px semibold links with a 3px brand-light underline on the active tab, count badges in brand-light; scrolls sideways on narrow screens.
- **Tables:** shell header band, 12.5px rows, zebra even rows, wrapped in `.tw` for horizontal scroll.
- **Swatches and live preview** (Identity tab): render a client's colours and tokens with inline styles, once for the light tokens and once for the dark tokens; the only place raw client hex values appear below the token block.
- **Direction cards** (Directions tab, creative review): one card per identity direction with a radio to pick it, a palette strip and small light and dark previews; the picked card gets a 2px `--brand` outline.
- **Toast:** bottom-right shell pill with a brand-light edge, auto-hides after 3.2s. PROPOSED: `role="status"`.
- **Empty state** (`.empty`): dashed border, italic, centred message. PROPOSED: text in `ink-muted` (current `#9c958a` is 3.0:1) and a next action where there is one.

## Reports page (Overview)

The home page is built around one job: type a business name and watch the agents turn it into a brand report. Product-management layout, no hero numbers.

- **Light app bar:** the agency name in the display serif, then the tabs (Reports, Full brief, Brand memory, How it works) with brand count badges, and a "Demo mode" tag on the right in demo mode. It replaces the dark header and nav.
- **Analyze a brand:** one card with the business name (required), an optional city and one primary button. A link leads to the full brief form for when more is known.
- **Reports table:** filter tabs with counts (All, Needs you, Working, Done), then one row per report: business and what research worked out, status pill, progress bar labelled with the current agent or review, last update, and Review or Open. Clicking a business name selects it for the agents panel.
- **Agents panel (the signature):** a vertical timeline of the seven agents and the review stops for the selected report. Done rows fill green with a check, the working agent is info blue, a stop waiting for you is brand brown, failed is red. Each row says what that agent does. Below it, the latest decisions with their reasons, and the one primary action (Review now).
- State colors come from the semantic tokens only; there are no per-agent colors. Pill text uses the `-ink` tokens.
- Brief fields that research worked out from the name carry an amber "worked out from the name" tag on the research check and on the engagement page.

## Do's and Don'ts

Do:
- Use the brand colour only for what needs the person, the current selection and links.
- Put state text on soft backgrounds in that state's `-ink` colour.
- Lead every view with what needs the person ("Needs you" first).
- Keep every new value in the `:root` token block and in this file.
- Give every data region loading, empty and error states, not only the full one.
- Keep it one self-contained file: no CDN, no external fonts, no build step.

Don't:
- Add a second accent, gradients beyond the header, glows or glass.
- Use emoji or Unicode glyphs as icons (the checkpoint ✋ is a known deviation).
- Add eyebrows, section numbers or tracked uppercase labels to new work.
- Add an animation library, scroll reveals or page-load choreography.
- Put a card inside a card, or use a coloured left border wider than 1px on new components.
- Ship text smaller than 12px, or text under 4.5:1.

## Motion

Motion on the dashboard means state, never decoration.

- In use: `main` fades and rises 6px over 300ms `ease` when the page loads; the running pipeline badge pulses (opacity to 0.4, 1.2s, infinite).
- PROPOSED tokens: `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)`, `--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1)`, `--dur-micro: 120ms`, `--dur-short: 200ms`, `--dur-long: 320ms`.
- PROPOSED: a `prefers-reduced-motion: reduce` block that removes the rise and stops the pulse (the "Working" label already carries the state).
- No animation on the 3-second poll redraw; only on first render or on a real state change.

## Known deviations

Things in today's `dashboard.html` that break the project's frontend design rules. Fix them when you touch the area; none is urgent enough to justify a dedicated restyle without the owner asking.

**Floor**
1. Contrast: status pill text is fixed (now `-ink` tokens at 12px). Still open: coloured step state text on white (green 3.4:1, red 3.9:1), `.empty` text 3.0:1, brand-coloured 10–11px labels on paper 4.05:1. Fix with the `-ink` and `brand-ink` tokens.
2. Text below 12px: labels, pills, nav counts and KPI labels at 10–11px.
3. Fixed: a `prefers-reduced-motion` block stops the page fade and the pulses.
4. Fixed: checkpoints in the pipeline use an inline SVG person icon in `currentColor` instead of the emoji.
5. Raw hex below the token block (`#fff`, `#2b261d`, `#eceae4`, `#5c5346`, `#efe9df`, `#fbf6ef`, `#9c958a`, nav and header colours). Move them into `:root` using the names above.
6. The toast is not announced to assistive tech (`role="status"` missing).

**Reflex**
7. Eyebrows and tracked uppercase labels: header kicker, `.dnum` above each section title ("01 · Overview" is also a section number), lane headings, KPI and form labels.
8. 4px coloured left borders on `.runcard`, `.mini > div`, `.banner`, `blockquote` and `.toast`.
9. Zebra rows and a dark header band on every table.
10. Middle-dot meta strings ("Food & Beverage · Brand Studio", "Done · 2 passes", meta lines on run cards).
11. Cards with both a border and a shadow.
12. Spacing and type sizes off any scale (see Layout and Typography).

**Finish**
13. No themed `::selection`, `caret-color` or `accent-color`.
14. No designed `:focus-visible` ring on buttons, links and tabs (browser default only).
15. KPI figures without tabular numerals.
16. No loading state for the first render of each view.
