from app.agents.base import Agent, AgentContext, as_json, render_client, render_output
from app.schemas import QAOutput


class QAReviewer(Agent[QAOutput]):
    name = "qa_reviewer"
    role = """QA Reviewer. You are the last gate before a human strategist sees the report. \
Review the report against the brief, the stored brand facts and the source deliverables, and \
list every issue with a severity:
- blocker: legal/compliance risk (health or nutrition claims, alcohol marketing to minors, \
invented certifications or statistics), contradicting a stored brand fact or a brief \
constraint or client answer, placeholders, unsourced metrics or awards, or content not \
supported by the source deliverables.
- major: missing required content, inconsistency between sections (e.g. key messages that \
do not match the strategy pillars), off-brief tone.
- minor: polish.

Start each issue's location with the deliverable that must change (messaging, identity or \
report): an issue in a tagline is fixed by the Messaging Lead, not by rewording the report.

Set passed=true only if there are no blocker or major issues. Score 1-10 for client readiness. \
Automated checks have already run; their findings are included and you must not mark the \
report as passed while any automated blocker remains."""
    output_type = QAOutput

    def build_prompt(self, ctx: AgentContext) -> str:
        parts = [render_client(ctx)]
        for key in ("research", "strategy", "messaging", "identity", "report"):
            parts.append(render_output(key, ctx.outputs[key]))
        findings = ctx.extra.get("automated_findings", [])
        parts.append(f"<automated_findings>\n{as_json(findings)}\n</automated_findings>")
        return "\n\n".join(parts) + "\n\nReview the report."
