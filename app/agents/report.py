from app.agents.base import Agent, AgentContext, render_brief, render_answers, render_feedback, render_output
from app.schemas import ReportOutput


class ReportProducer(Agent[ReportOutput]):
    name = "report_producer"
    role = """Report Producer. You assemble the team's approved work into one client-ready \
brand report. Include sections with headings that name Research, Strategy, Messaging and \
Identity, plus Social media when a social plan is included (you may add others), an executive summary of 250 words or fewer, and concrete next \
steps. Write in clear Markdown for a business owner, not an agency insider.

Do not introduce new claims, numbers or creative ideas that are not in the source deliverables. \
Never leave placeholders. Research's data tables (market facts, online presence, competitors, \
each with its source) are added to the report automatically after your sections, so refer to \
them instead of repeating the figures in prose. The full social plan (calendar and every \
script) is a separate deliverable, so the Social media section summarizes platforms, pillars \
and the first scripts instead of copying them."""
    output_type = ReportOutput

    def build_prompt(self, ctx: AgentContext) -> str:
        parts = [render_brief(ctx.brief) + render_answers(ctx.answers)]
        for key in ("research", "strategy", "messaging", "identity", "social"):
            if key in ctx.outputs:
                parts.append(render_output(key, ctx.outputs[key]))
        return "\n\n".join(parts) + render_feedback(ctx.feedback) + "\n\nProduce the client report."
