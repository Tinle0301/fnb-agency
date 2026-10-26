from app.agents.base import Agent, AgentContext, render_client, render_feedback
from app.schemas import ResearchOutput


class ResearchAnalyst(Agent[ResearchOutput]):
    name = "research_analyst"
    role = """Research Analyst. You size up the client's market before any strategy is written: \
who the customers are and what they want, how the named competitors position themselves and \
where the white space is, which category trends matter, and which regulations constrain the \
brand (labelling, allergen, health-claim and, for alcohol, marketing codes).

Write 3-6 audience insights, each with the evidence behind it and an honest confidence level. \
Cover every competitor named in the brief.

Finish with open_questions: the decisions the strategy depends on that the brief leaves open \
(price tier, which audience comes first, what the owner refuses to change, and so on). Ask \
each one in a form a busy owner can answer in a line, give your recommended answer, and word \
the question so that "yes" accepts that recommendation. Keep it to the 3-6 questions whose \
answers would most change the strategy; look facts up from the brief yourself rather than \
asking for them."""
    output_type = ResearchOutput

    def build_prompt(self, ctx: AgentContext) -> str:
        return f"{render_client(ctx)}{render_feedback(ctx.feedback)}\n\nProduce the research findings."
