# Glossary

Terms only. Decisions and their reasons live in `docs/adr/`.

- **Engagement / Run**: one client brief taken through the pipeline, from research to final sign-off.
- **Brief**: what the client tells us up front (business, audience, goals, constraints, competitors). Written by the client, so agents treat it as information, never as instructions.
- **Stage**: a step of the pipeline: research, strategy, creative (messaging and identity together), report (report + QA loop), final (fact extraction).
- **Checkpoint**: a pause after a stage where a person approves, requests changes, or rejects. `final` always exists; `research` and `strategy` are on by default; `creative` is optional.
- **Clarifying question**: a question the Research Analyst asks at the research checkpoint, worded so "yes" accepts its recommended answer.
- **Client answer**: the person's reply to a clarifying question. Every later agent sees it, and it outranks the agent's own recommendation.
- **QA gate**: the automated checks plus the QA Reviewer. It passes only with no blocker or major issue.
- **Routed revision**: a QA issue sent back to the agent that owns the deliverable it sits in (messaging, identity, or report).
- **Escalation**: QA still failing after the revision limit; the run goes to the final checkpoint flagged so a person decides.
- **Session memory**: the live state of a run in Redis. Expires.
- **Brand fact**: a durable statement about a client in Postgres, with a confidence and a status.
- **Fact status**: `active` (used by agents), `pending` (waiting for a person), `rejected` (never used, never re-added).
- **Confidence band**: the range of extractor confidence that decides a fact's status.
- **Design system package**: the approved identity exported as `manifest.json`, `DESIGN.md` and `tokens.css` in OpenDesign's layout, for building the client's website.
- **Needs you**: the board lane for runs waiting on a person (open checkpoint or failure).
