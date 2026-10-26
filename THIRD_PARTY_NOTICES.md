# Third-party notices

Ideas and some rule lists in this project are adapted from these open-source projects.

- **OpenDesign** (github.com/nexu-io/open-design), Apache-2.0. The design-system package layout (`manifest.json` with `od-design-system-project/v1`, `DESIGN.md` sections, role-named `tokens.css`) used by `app/exports.py`; color contrast minimums, accent discipline and the default-indigo list from `craft/color.md` and `craft/anti-ai-slop.md` (themselves adapted from refero_skill, MIT) used in `app/checks.py`; strategy-first symbol logic, logo concept methods and tagline style from `skills/brandkit` (from Leonxlnx/taste-skill, MIT) used in the Identity and Messaging prompts.
- **mattpocock/skills** (github.com/mattpocock/skills), MIT. The grilling approach (questions with a recommended answer, worded so "yes" accepts it) used for the Research Analyst's clarifying questions; `GLOSSARY.md` and one-paragraph ADRs from `domain-modeling`; tests at public seams from `tdd`.
- **Agent Orchestrator** (github.com/OrchestratorInc/agent-orchestrator), Apache-2.0. Attention-zone board ("Needs you" first), feedback routed back to the worker that owns the change, and notifying a person only when they are needed.
- **Don't Be Michael** (github.com/agentvivekkumar/dontbemichael), MIT. Marking text written outside the business as untrusted and flagging instruction-like lines (`app/untrusted.py`, ported from `src/shared/untrustedText.ts`); house rules on stating only what can be traced to a source.
