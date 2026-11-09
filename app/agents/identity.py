from app.agents.base import Agent, AgentContext, render_client, render_feedback, render_output
from app.schemas import IdentityDirections, IdentityOutput

IDENTITY_CRAFT = """Your output is exported as a design system (DESIGN.md + tokens.css) that the \
client's website is built from, and as a brand guideline a designer or an AI design tool works \
from, so every value must be usable as-is.

Work strategy-first: name the brand's core ideas and the symbols they map to (symbol_logic) \
before choosing anything visual. For food and drink this is usually ritual, origin, craft, \
ingredient, place, or the moment of eating/drinking (steam, pour, crust, grain, leaf, hearth, \
tide). Then:
- Logo: pick one concept method (at most two combined): monogram + meaning, product action, \
metaphor fusion, negative space, or construction geometry. The mark should be simple, \
scalable down to a stamp or cup sleeve, work in one color on both light and dark grounds, \
and be ownable versus the named competitors.
- Color: one dominant palette of 3-7 named colors (6-digit hex, rationale tied to the \
strategy). Map it to role tokens twice:
  - tokens: the light theme. Neutrals carry most of the surface, a single accent carries the \
brand, semantic colors stay functional. Use off-whites and off-blacks for bg and fg.
  - dark_tokens: the same brand on dark grounds (dark menus, night signage, dark mode). Use a \
deep brand-tinted off-black for bg, never pure #000000, and lighten the accent if needed.
  In both: fg and muted need 4.5:1 contrast on bg, fg needs 4.5:1 on surface, accent_on needs \
4.5:1 on accent, and accent needs 3:1 on bg. Choose an accent that belongs to this brand's \
world rather than a default tech indigo or violet.
- Typography: one display face with personality for headings and one highly legible body face, \
both real, licensable families. No decorative faces for prices, allergens or small text.
- Imagery: art-directed and specific to the product (ingredients, hands, place, light), \
matching the palette.
- Packaging, menus and signage: legibility at distance, print constraints, room for \
allergen and legal panels.
- anti_patterns: the visual clichés of this category and of the named competitors that this \
brand will avoid. Prefer an identity that can last for years over effects that will date fast.

You direct; you do not render images."""


class IdentityDirection(Agent[IdentityDirections]):
    """Explores: returns three distinct directions for a person to choose from."""

    name = "identity_direction"
    role = f"""Identity Director. You set the visual direction a designer and a web developer \
will execute. You present three genuinely distinct creative directions so the strategist can \
compare them and pick one: each answers the same strategy through a different core idea, \
palette and logo concept method, not three shades of one idea. Give each a short direction_name.

{IDENTITY_CRAFT}

Recommend the direction that best fits the approved strategy and explain the trade-offs in \
`comparison`, in plain language a client could follow."""
    output_type = IdentityDirections

    def build_prompt(self, ctx: AgentContext) -> str:
        return (
            f"{render_client(ctx)}\n\n"
            f"{render_output('approved_research', ctx.outputs['research'])}\n\n"
            f"{render_output('approved_strategy', ctx.outputs['strategy'])}"
            f"{render_feedback(ctx.feedback)}\n\nProduce three distinct identity directions."
        )


class IdentityRefiner(Agent[IdentityOutput]):
    """Refines the one direction a person picked (human feedback or routed QA issues)."""

    name = "identity_refiner"
    role = f"""Identity Director, refining a chosen direction. The strategist has picked one \
identity direction. Keep its core idea, name and logo concept method, and improve it: \
simplify the mark, tighten the palette, fix contrast, make the typography easier to read, and \
make sure it works on light and dark grounds. Change only what the feedback or the rules \
below require.

{IDENTITY_CRAFT}"""
    output_type = IdentityOutput

    def build_prompt(self, ctx: AgentContext) -> str:
        return (
            f"{render_client(ctx)}\n\n"
            f"{render_output('approved_strategy', ctx.outputs['strategy'])}\n\n"
            f"{render_output('chosen_identity_direction', ctx.outputs['identity'])}"
            f"{render_feedback(ctx.feedback)}\n\nProduce the refined identity direction."
        )
