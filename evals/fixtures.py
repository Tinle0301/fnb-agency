"""Golden briefs and hand-checked agent outputs.

Used three ways:
- the offline test suite feeds them to a fake LLM so the whole pipeline runs without API calls;
- the grader tests check that every grader passes these and fails planted-defect variants;
- the live eval runner uses them as fixed upstream context, so each agent is scored in isolation
  (a weak strategy cannot drag down the messaging score).
"""

from __future__ import annotations

from app.schemas import (
    ClientBrief,
    ExtractedFact,
    FactExtraction,
    IdentityDirections,
    IdentityOutput,
    MessagingOutput,
    QAOutput,
    ReportOutput,
    ResearchOutput,
    SocialOutput,
    StrategyOutput,
)

BREWERY_BRIEF = ClientBrief(
    client_id="harbor-hops",
    client_name="Harbor Hops Brewing",
    business_type="craft brewery and taproom",
    location="Portland, Maine",
    target_audience="locals aged 25-45 who value small-batch beer and waterfront hangouts",
    goals=["Rebrand ahead of the first canning run", "Stand apart from tourist-focused breweries"],
    constraints=["Keep the name Harbor Hops", "Budget covers one photo shoot", "Cans must fit a 16oz sleeve label"],
    competitors=["Allagash", "Bissell Brothers"],
    products=["Low Tide Hazy IPA", "Sea Salt Gose", "Fog Line Pilsner"],
    notes="Founded 2019 by two former lobstermen. Taproom is on a working pier. Grain comes from Maine Grains in Skowhegan.",
)

BAKERY_BRIEF = ClientBrief(
    client_id="crumb-and-root",
    client_name="Crumb & Root",
    business_type="plant-based bakery",
    location="Austin, Texas",
    target_audience="busy professionals and parents looking for plant-based treats that taste indulgent",
    goals=["Launch wholesale to local coffee shops", "Grow weekend pre-orders"],
    constraints=["No health or nutrition claims", "All products are nut-free"],
    competitors=["Capital City Bakery", "Sweet Ritual"],
    products=["Cardamom morning bun", "Brown butter-style cookie", "Seasonal fruit galette"],
    notes="Owner trained in a French pastry kitchen before going plant-based.",
)

BRIEFS = {"brewery": BREWERY_BRIEF, "bakery": BAKERY_BRIEF}


BREWERY_RESEARCH = ResearchOutput(
    business_profile={
        "business_type": BREWERY_BRIEF.business_type,
        "location": BREWERY_BRIEF.location,
        "target_audience": BREWERY_BRIEF.target_audience,
        "goals": BREWERY_BRIEF.goals,
        "basis": "Copied from the brief.",
    },
    market_summary=(
        "Portland has one of the densest craft beer scenes per capita in the US. Visitors drive taproom "
        "traffic in summer while locals sustain it the rest of the year, so a brewery that wins locals "
        "has steadier revenue."
    ),
    market_facts=[
        {"topic": "Breweries in Portland", "value": "About 20 within the city", "source_url": "https://www.visitportland.com/"},
        {"topic": "Peak season", "value": "Summer cruise season drives waterfront traffic", "source_url": ""},
    ],
    online_presence=[
        {"channel": "Website", "status": "unverified", "detail": "Not checked yet", "source_url": ""},
        {"channel": "Instagram", "status": "not_found", "detail": "No account found under the brewery name", "source_url": ""},
    ],
    audience_insights=[
        {
            "insight": "Locals avoid taprooms that feel built for cruise-ship crowds.",
            "evidence": "Brief goal: stand apart from tourist-focused breweries; inferred from the waterfront location.",
            "confidence": "medium",
        },
        {
            "insight": "Provenance stories (who brewed it, where the grain came from) drive repeat visits.",
            "evidence": "Brief notes: founders are former lobstermen; grain from Maine Grains.",
            "confidence": "high",
        },
        {
            "insight": "Cans are bought for porches, boats and beaches, so the label must read at a glance.",
            "evidence": "Inferred from the canning launch and the 16oz sleeve constraint.",
            "confidence": "medium",
        },
    ],
    competitor_landscape=[
        {
            "name": "Allagash",
            "where": "Portland, about 5 km from the waterfront",
            "positioning": "Belgian-style pioneer with a polished, heritage feel.",
            "gap_we_can_own": "A working-waterfront voice that is rougher and more local.",
            "source_url": "https://www.allagash.com/",
        },
        {
            "name": "Bissell Brothers",
            "where": "Portland",
            "positioning": "Hype-driven hazy IPAs with bold graphic cans.",
            "gap_we_can_own": "Calm, maritime confidence instead of hype.",
            "source_url": "",
        },
    ],
    category_trends=["Lower-ABV session beers", "Local grain sourcing", "Taproom events over distribution"],
    regulatory_notes=[
        "TTB labelling rules apply to cans (ABV, government warning, net contents).",
        "Brewers Association marketing code: no appeal to under-21s, no links between drinking and success.",
    ],
    open_questions=[
        {
            "question": "Should the cans carry the founders' lobstering story on the back panel?",
            "why_it_matters": "Decides whether provenance is a headline or a supporting detail.",
            "recommended_answer": "Yes, a two-line story on the back panel.",
        },
        {
            "question": "Is the year-round local regular the primary audience, ahead of summer visitors?",
            "why_it_matters": "Sets tone and where marketing money goes.",
            "recommended_answer": "Yes, locals first; visitors follow.",
        },
    ],
)

BREWERY_STRATEGY = StrategyOutput(
    positioning_statement=(
        "For Portland locals who want a real waterfront local, Harbor Hops is the pier-side brewery that "
        "pours honest, sessionable beer because it is run by former lobstermen who brew with Maine grain."
    ),
    brand_promise="A pint that tastes like the working waterfront, poured by people who worked it.",
    pillars=[
        {
            "name": "Working Waterfront",
            "description": "Rooted in the pier and the people who work it.",
            "proof_points": ["Taproom on a working pier", "Founded by two former lobstermen"],
        },
        {
            "name": "Maine Grown",
            "description": "Local grain and local names.",
            "proof_points": ["Grain from Maine Grains, Skowhegan", "Beers named for coastal conditions"],
        },
        {
            "name": "Easy Company",
            "description": "Sessionable beer and an unpretentious room.",
            "proof_points": ["Fog Line Pilsner and Sea Salt Gose are session styles", "Locals-first taproom events"],
        },
    ],
    personality_traits=["steady", "salty", "warm", "plainspoken"],
    differentiation="Where Allagash is heritage polish and Bissell is hype, Harbor Hops is the calm local on the pier.",
    risks=["Maritime themes are common in Maine; the execution must be specific to this pier."],
)

BREWERY_MESSAGING = MessagingOutput(
    tagline_options=["Brewed where the boats come in.", "Your local, on the pier.", "Low tide. High pour."],
    elevator_pitch=(
        "Harbor Hops is Portland's pier-side brewery, started by two former lobstermen who brew easy-drinking "
        "beer with Maine grain and pour it a few steps from the boats."
    ),
    key_messages=[
        {"pillar": "Working Waterfront", "message": "Our taproom sits on a working pier.", "proof": "Taproom location"},
        {"pillar": "Maine Grown", "message": "Brewed with grain from Skowhegan.", "proof": "Maine Grains partnership"},
        {"pillar": "Easy Company", "message": "Beer for a second round, not a lecture.", "proof": "Session styles on tap"},
    ],
    tone_of_voice={
        "summary": "Plainspoken, dry humor, a little salt.",
        "do": ["Use short sentences", "Name real places on the waterfront"],
        "dont": ["Use beer-snob jargon", "Use pirate clichés"],
    },
    sample_copy=[
        {"channel": "Can back panel", "copy_text": "Two lobstermen, one pier, Maine grain. Drink it cold."},
        {"channel": "Instagram", "copy_text": "Fog rolled in, Fog Line is on. Doors open at 3."},
        {"channel": "Menu board", "copy_text": "Low Tide Hazy IPA: soft, bright, best before the boats come back."},
    ],
)

BREWERY_IDENTITY = IdentityOutput(
    direction_name="Tide Line",
    visual_direction_summary="Weathered maritime utility: tide charts, rope, salt-faded paint on the pier.",
    mood_keywords=["salt-worn", "steady", "utilitarian", "warm"],
    symbol_logic="Working waterfront and tide map to a buoy and tide line; Maine grain maps to a barley ear.",
    color_palette=[
        {"name": "Harbor Teal", "hex": "#1F5C5A", "rationale": "Deep water off the pier; the single accent."},
        {"name": "Sail Cream", "hex": "#F6F1E7", "rationale": "Sun-faded canvas for backgrounds."},
        {"name": "Tar Black", "hex": "#1C2321", "rationale": "Dock tar for type."},
        {"name": "Buoy Red", "hex": "#B5452B", "rationale": "Small doses on cans for shelf pop."},
    ],
    tokens={
        "bg": "#F6F1E7",
        "surface": "#FFFDF8",
        "fg": "#1C2321",
        "muted": "#55605B",
        "border": "#DDD3C2",
        "accent": "#1F5C5A",
        "accent_on": "#FFFDF8",
        "success": "#3F7A46",
        "warn": "#A8641C",
        "danger": "#A33A2F",
    },
    dark_tokens={
        "bg": "#121A19",
        "surface": "#1B2624",
        "fg": "#F3EDE2",
        "muted": "#A9B3AE",
        "border": "#2E3B38",
        "accent": "#5FA8A3",
        "accent_on": "#0E1514",
        "success": "#7DBA84",
        "warn": "#E0A458",
        "danger": "#E57F72",
    },
    typography={
        "display": "Fraunces",
        "body": "IBM Plex Sans",
        "rationale": "A characterful serif echoes hand-painted boat names; Plex reads cleanly on menus.",
    },
    logo_concept_method="metaphor_fusion",
    logo_direction="A buoy whose waterline doubles as the H crossbar; works as a can stamp and a taproom sign.",
    imagery_style="Early-morning pier light, hands at work, cans on weathered wood; no stock lighthouse shots.",
    packaging_and_signage_notes="Beer name in display face at top third of the 16oz sleeve; keep the TTB panel clear.",
    anti_patterns=["Pirate and anchor clichés", "Bissell-style neon hype graphics"],
)

# Two alternatives the Identity Director offers next to Tide Line (the recommended one).
BREWERY_IDENTITY_SIGNAL = IdentityOutput.model_validate(
    BREWERY_IDENTITY.model_dump()
    | {
        "direction_name": "Signal Flag",
        "visual_direction_summary": "Bold nautical signal flags: flat blocks of color, crisp geometry, loud on the shelf.",
        "mood_keywords": ["bold", "graphic", "confident", "playful"],
        "symbol_logic": "Harbor communication maps to signal flags; each beer gets its own flag pattern.",
        "color_palette": [
            {"name": "Flag Red", "hex": "#B8322A", "rationale": "Signal flag red; the single accent."},
            {"name": "Chart Paper", "hex": "#F4F0E6", "rationale": "Nautical chart paper backgrounds."},
            {"name": "Navy Ink", "hex": "#1B2433", "rationale": "Chart ink for type."},
            {"name": "Brass", "hex": "#B58A3C", "rationale": "Ship brass for small details."},
        ],
        "tokens": BREWERY_IDENTITY.tokens.model_dump()
        | {"bg": "#F4F0E6", "fg": "#1B2433", "accent": "#B8322A", "accent_on": "#FFFDF8", "border": "#DCD4C2"},
        "dark_tokens": BREWERY_IDENTITY.dark_tokens.model_dump()
        | {"bg": "#131A26", "surface": "#1C2533", "accent": "#E4675C", "accent_on": "#131A26"},
        "typography": {
            "display": "Archivo Black",
            "body": "Archivo",
            "rationale": "Heavy grotesque reads like stenciled hull numbers; one family keeps it tight.",
        },
        "logo_concept_method": "construction_geometry",
        "logo_direction": "A square signal flag split on the diagonal into an H; prints as one color on cans.",
    }
)

BREWERY_IDENTITY_GRAIN = IdentityOutput.model_validate(
    BREWERY_IDENTITY.model_dump()
    | {
        "direction_name": "Grain and Rope",
        "visual_direction_summary": "Hand-made and earthy: Maine grain, coiled rope, letterpress texture.",
        "mood_keywords": ["handmade", "earthy", "quiet", "honest"],
        "symbol_logic": "Maine grain and rope work map to a barley ear tied in a sailor's knot.",
        "color_palette": [
            {"name": "Malt Brown", "hex": "#7A4A24", "rationale": "Toasted malt; the single accent."},
            {"name": "Oat", "hex": "#F3EBDD", "rationale": "Raw grain for backgrounds."},
            {"name": "Peat", "hex": "#2A2320", "rationale": "Dark soil for type."},
            {"name": "Kelp", "hex": "#4F6B4A", "rationale": "Seaweed green for small details."},
        ],
        "tokens": BREWERY_IDENTITY.tokens.model_dump()
        | {"bg": "#F3EBDD", "fg": "#2A2320", "accent": "#7A4A24", "accent_on": "#FFFDF8", "border": "#DCCFBA"},
        "dark_tokens": BREWERY_IDENTITY.dark_tokens.model_dump()
        | {"bg": "#1A1512", "surface": "#251E1A", "accent": "#C99566", "accent_on": "#1A1512"},
        "typography": {
            "display": "Recoleta",
            "body": "Source Sans 3",
            "rationale": "A soft, warm serif feels hand-set; Source Sans keeps menus easy to read.",
        },
        "logo_concept_method": "monogram_meaning",
        "logo_direction": "An HH monogram whose crossbars are a knotted rope around a barley ear.",
    }
)

BREWERY_DIRECTIONS = IdentityDirections(
    directions=[BREWERY_IDENTITY, BREWERY_IDENTITY_SIGNAL, BREWERY_IDENTITY_GRAIN],
    recommended=0,
    comparison=(
        "Tide Line is the calm local on the pier and fits the strategy best. Signal Flag is louder and wins "
        "on the shelf but drifts toward the tourist look. Grain and Rope leans on Maine grain over the water."
    ),
)

BREWERY_REPORT = ReportOutput(
    title="Harbor Hops Brewing: Brand Direction",
    executive_summary=(
        "Harbor Hops should own the role of Portland's calm local on the pier. The brand leans on its working "
        "waterfront, Maine grain and easy-drinking beer, with a plainspoken voice and a weathered maritime look "
        "built around Harbor Teal."
    ),
    sections=[
        {"heading": "Research findings", "body_markdown": "Locals want a taproom that is not built for tourists."},
        {"heading": "Brand strategy", "body_markdown": "Positioning: the pier-side brewery run by former lobstermen."},
        {"heading": "Messaging", "body_markdown": "Lead tagline: *Brewed where the boats come in.*"},
        {"heading": "Visual identity", "body_markdown": "Harbor Teal accent, Fraunces and IBM Plex Sans, buoy mark."},
    ],
    next_steps=["Brief the designer on the buoy mark", "Plan the single photo shoot at the pier at dawn"],
)


def _script(title: str, platform: str, fmt: str, pillar: str, hook: str, shot: str) -> dict:
    return {
        "title": title,
        "platform": platform,
        "format": fmt,
        "pillar": pillar,
        "goal": "Make a local regular want to stop by this week.",
        "hook": hook,
        "scenes": [
            {"time": "0-3s", "shot": shot, "voiceover": "", "on_screen_text": hook},
            {"time": "3-12s", "shot": "Hands pour a pint at the taproom bar, pier through the window.", "voiceover": "Brewed where the boats come in.", "on_screen_text": ""},
            {"time": "12-18s", "shot": "Wide shot of the taproom at golden hour.", "voiceover": "", "on_screen_text": "Harbor Hops, on the pier"},
        ],
        "call_to_action": "Come by the taproom on the pier.",
        "caption": "Brewed where the boats come in. See you on the pier.",
        "hashtags": ["#PortlandMaine", "#HarborHops", "#MaineBeer"],
        "production_notes": "Phone on a small tripod, natural light, Harbor Teal apron, no music with lyrics.",
        "confirm_before_posting": ["Taproom hours this week"],
    }


BREWERY_SOCIAL = SocialOutput(
    summary=(
        "Talk to Portland locals on Instagram and TikTok with short, calm videos from the pier. Every post shows "
        "the real people and grain behind the beer, so the brewery feels like a local's place, not a tourist stop."
    ),
    platforms=[
        {"platform": "Instagram", "role": "Main home for locals who plan nights out.", "formats": ["Reels 15-30s", "carousel"], "posts_per_week": 4, "best_times": "Thu-Sat late afternoon; test and adjust."},
        {"platform": "TikTok", "role": "Reach younger locals with behind-the-scenes clips.", "formats": ["TikTok 20-40s"], "posts_per_week": 3, "best_times": "Evenings; test and adjust."},
        {"platform": "Google Business Profile", "role": "Show up when people search for a taproom nearby.", "formats": ["photo update", "event post"], "posts_per_week": 1, "best_times": "Monday morning for the week's events."},
    ],
    content_pillars=[
        {"name": "Working Waterfront", "purpose": "Ties the beer to the pier (strategy pillar Working Waterfront).", "share_percent": 40, "example_topics": ["Dawn on the pier", "Boats coming in"]},
        {"name": "Maine Grown", "purpose": "Shows the grain and the people (strategy pillar Maine Grown).", "share_percent": 35, "example_topics": ["Maine Grains delivery", "Brew day"]},
        {"name": "Easy Company", "purpose": "Invites locals in (strategy pillar Easy Company).", "share_percent": 25, "example_topics": ["Trivia night", "Meet the bar staff"]},
    ],
    scripts=[
        _script("Dawn on the pier", "Instagram", "Reel 18s", "Working Waterfront", "5 a.m. on the pier.", "Boats leave at first light."),
        _script("Where the grain comes from", "Instagram", "Reel 20s", "Maine Grown", "This beer started on a Maine farm.", "Grain sacks unloaded at the brewery."),
        _script("Brew day in 20 seconds", "TikTok", "TikTok 20s", "Maine Grown", "Ever seen a brew day?", "Steam rising from the kettle."),
        _script("Meet the lobstermen", "TikTok", "TikTok 30s", "Working Waterfront", "We used to haul traps.", "Founders on the dock with old buoys."),
        _script("Trivia night", "Instagram", "Story 3 frames", "Easy Company", "Thursday. Trivia. Pier.", "Crowd laughing at the bar."),
        _script("Your seat at the bar", "TikTok", "TikTok 15s", "Easy Company", "Grab a seat at the bar.", "Empty stool, pint slides in."),
    ],
    calendar=[
        {"week": 1, "day": "Tue", "platform": "Instagram", "pillar": "Working Waterfront", "idea": "Dawn on the pier", "script_title": "Dawn on the pier"},
        {"week": 1, "day": "Thu", "platform": "TikTok", "pillar": "Maine Grown", "idea": "Brew day", "script_title": "Brew day in 20 seconds"},
        {"week": 2, "day": "Tue", "platform": "Instagram", "pillar": "Maine Grown", "idea": "Grain delivery", "script_title": "Where the grain comes from"},
        {"week": 2, "day": "Thu", "platform": "Instagram", "pillar": "Easy Company", "idea": "Trivia night", "script_title": "Trivia night"},
    ],
    kpis=[
        {"metric": "Instagram saves per Reel", "target": "Baseline in month 1, then grow month on month", "why": "Saves show locals plan to visit."},
        {"metric": "Taproom visits mentioning social", "target": "Ask at the bar and count weekly; baseline in month 1, then grow", "why": "Ties posts to real visits."},
    ],
    community_rules=[
        "Reply within a day, in the same plain voice as the posts.",
        "Thank people for complaints, move details to a direct message, never argue in public.",
    ],
)

QA_PASS = QAOutput(passed=True, score=8, issues=[], summary="On brief and compliant; ready for the strategist.")

QA_FAIL = QAOutput(
    passed=False,
    score=4,
    issues=[
        {
            "severity": "blocker",
            "location": "messaging.tagline_options",
            "problem": "Tagline implies a health benefit.",
            "suggested_fix": "Replace with a provenance line.",
        }
    ],
    summary="One compliance blocker in messaging.",
)

BREWERY_FACTS = FactExtraction(
    facts=[
        ExtractedFact(
            category="identity",
            statement="Harbor Hops Brewing was founded in 2019 by two former lobstermen.",
            source="client_brief",
            evidence="Brief notes",
            confidence=0.97,
        ),
        ExtractedFact(
            category="product",
            statement="Harbor Hops brews with grain from Maine Grains in Skowhegan.",
            source="client_brief",
            evidence="Brief notes",
            confidence=0.95,
        ),
        ExtractedFact(
            category="visual",
            statement="Harbor Hops' accent color is Harbor Teal #1F5C5A.",
            source="approved_output",
            evidence="Approved identity direction",
            confidence=0.75,
        ),
        ExtractedFact(
            category="audience",
            statement="Harbor Hops may expand to Boston next year.",
            source="approved_output",
            evidence="Speculation in research",
            confidence=0.3,
        ),
    ]
)

BREWERY_OUTPUTS = {
    ResearchOutput: BREWERY_RESEARCH,
    StrategyOutput: BREWERY_STRATEGY,
    MessagingOutput: BREWERY_MESSAGING,
    IdentityDirections: BREWERY_DIRECTIONS,
    IdentityOutput: BREWERY_IDENTITY,  # what the refiner returns
    SocialOutput: BREWERY_SOCIAL,
    ReportOutput: BREWERY_REPORT,
    QAOutput: QA_PASS,
    FactExtraction: BREWERY_FACTS,
}
