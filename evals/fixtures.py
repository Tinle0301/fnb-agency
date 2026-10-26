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
    IdentityOutput,
    MessagingOutput,
    QAOutput,
    ReportOutput,
    ResearchOutput,
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
    market_summary=(
        "Portland has one of the densest craft beer scenes per capita in the US. Visitors drive taproom "
        "traffic in summer while locals sustain it the rest of the year, so a brewery that wins locals "
        "has steadier revenue."
    ),
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
            "positioning": "Belgian-style pioneer with a polished, heritage feel.",
            "gap_we_can_own": "A working-waterfront voice that is rougher and more local.",
        },
        {
            "name": "Bissell Brothers",
            "positioning": "Hype-driven hazy IPAs with bold graphic cans.",
            "gap_we_can_own": "Calm, maritime confidence instead of hype.",
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
    IdentityOutput: BREWERY_IDENTITY,
    ReportOutput: BREWERY_REPORT,
    QAOutput: QA_PASS,
    FactExtraction: BREWERY_FACTS,
}
