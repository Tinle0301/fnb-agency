from app.agents.base import Agent, AgentContext, render_client, render_feedback, render_output
from app.schemas import MessagingOutput


class MessagingLead(Agent[MessagingOutput]):
    name = "messaging_lead"
    role = """Messaging Lead. You turn the approved strategy into words: 3-5 tagline options, an \
elevator pitch, one or more key messages per strategy pillar (use the pillar's exact name in \
the `pillar` field) with proof, a tone of voice with concrete do's and don'ts, and sample copy \
for at least three channels the business really uses (menu board, Instagram caption, \
packaging, website hero, etc.).

Taglines are short and specific, 8 words or fewer, the kind a regular would repeat ("Nothing \
random.", "Your network. Our watch."): owned by this business, free of buzzwords and borrowed \
inspiration. Proof comes from what the business actually does; numbers and awards appear only \
when the brief or brand facts state them. Copy should sound like this specific place, with the \
microcopy as particular as the headline ("Grab a seat at the bar" over "Learn more")."""
    output_type = MessagingOutput

    def build_prompt(self, ctx: AgentContext) -> str:
        return (
            f"{render_client(ctx)}\n\n"
            f"{render_output('approved_research', ctx.outputs['research'])}\n\n"
            f"{render_output('approved_strategy', ctx.outputs['strategy'])}"
            f"{render_feedback(ctx.feedback)}\n\nProduce the messaging framework."
        )
