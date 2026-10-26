from app.agents.base import Agent, AgentContext, render_client, render_feedback, render_output
from app.schemas import StrategyOutput


class BrandStrategist(Agent[StrategyOutput]):
    name = "brand_strategist"
    role = """Brand Strategist. From the approved research and the client's answers you define \
where the brand stands: a single positioning statement (for <audience>, <brand> is the <frame \
of reference> that <benefit> because <reason to believe>), the brand promise, 3-5 pillars each \
backed by concrete proof points the business can actually deliver, personality traits, the \
differentiation versus the named competitors, and the risks in this direction.

Every pillar traces back to a research insight, a client answer, or a stored brand fact. Where \
the client answered a clarifying question, their answer wins over your earlier recommendation."""
    output_type = StrategyOutput

    def build_prompt(self, ctx: AgentContext) -> str:
        return (
            f"{render_client(ctx)}\n\n{render_output('approved_research', ctx.outputs['research'])}"
            f"{render_feedback(ctx.feedback)}\n\nProduce the brand strategy."
        )
