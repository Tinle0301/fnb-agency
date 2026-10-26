# F&B Virtual Agency

A multi-agent brand agency for food and beverage clients. Six AI agents take a client brief to a finished brand report and a ready-to-build design system, with a person approving the work at each key step.

```
brief ─► Research Analyst ─[research ✋]─► Brand Strategist ─[strategy ✋]─► Messaging Lead ┐
                                                                             Identity Direction ┘
      ─► Report Producer ⇄ automated checks + QA Reviewer ─[final ✋]─► fact extractor ─► Postgres
```

✋ = human checkpoint. QA issues go back to the agent that owns them (a bad tagline goes to the Messaging Lead, a contrast failure to Identity Direction) up to `MAX_QA_REVISIONS` times; if QA still fails, the run reaches the final checkpoint flagged so a person decides.

## What's in it

| Piece | Where |
|---|---|
| FastAPI orchestrator and API | `app/main.py`, `app/orchestrator.py` |
| Six agents (prompts + output schemas) | `app/agents/`, `app/schemas.py` |
| Model API client (structured outputs, adaptive thinking, optional refusal fallback) | `app/llm.py` |
| Session memory in Redis (run state, event log, TTL) | `app/memory/session.py` |
| Brand facts and decision audit in Postgres | `app/memory/facts.py`, `migrations/` |
| Fact extractor (smaller model) with confidence bands | `app/memory/extractor.py` |
| Deterministic compliance and craft checks | `app/checks.py` |
| Untrusted-text flagging for briefs and client answers | `app/untrusted.py` |
| Structured JSON logging | `app/logging_setup.py` |
| Report and OpenDesign design-system export | `app/exports.py` |
| Review console | `app/static/console.html` (served at `/`) |
| Per-agent evaluations | `evals/` |
| Tests | `tests/` |

## Run it

Needs Python 3.11+ and Docker.

```bash
cp .env.example .env            # add your API key and the two model IDs
docker compose up -d            # Redis + Postgres
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Open http://localhost:8000 for the console, or http://localhost:8000/docs for the API.

To click through the workflow without an API key or Docker:

```bash
AGENCY_DEMO=1 AGENCY_STORAGE=memory uvicorn app.main:app
```

Demo mode returns the same Harbor Hops sample output for any brief, so use it to learn the flow, not to judge quality.

## The workflow

1. **Start a run**: `POST /runs` with a brief (the console's New run has a sample). The Research Analyst runs.
2. **Research checkpoint**: review the findings and answer the clarifying questions. Each comes with a recommended answer; edit it to what the client said. Answers reach every later agent and become high-confidence brand facts.
3. **Strategy checkpoint**: approve the positioning and pillars, or request changes with feedback (the stage re-runs with it).
4. **Creative + report**: Messaging Lead and Identity Direction run in parallel, then the Report Producer, automated checks and QA Reviewer loop.
5. **Final checkpoint**: read the report (`/runs/{id}/report.md`), the QA verdict, and download the design system (`/runs/{id}/design-system.zip`).
6. **Facts**: on final approval, the extractor saves durable facts. Pending ones show in the console to confirm or reject; active ones are given to every agent in the client's next engagement.

`POST /runs/{id}/decision` takes `{"checkpoint", "decision": "approve" | "request_changes" | "reject", "feedback", "answers"}`. A decision for a checkpoint that isn't open gets a 409, so a stale browser tab can't approve the wrong thing. Every decision is written to `checkpoint_decisions` in Postgres.

`GET /runs` returns the board: `needs_you`, `working`, `done`. Set `NOTIFY_WEBHOOK_URL` (a Slack incoming webhook works) to be pinged when a run needs you.

## Memory

- **Redis (short-term)**: run state and event log under `agency:run:*`, expiring after `SESSION_TTL_SECONDS` (7 days).
- **Postgres (long-term)**: `clients`, `brand_facts`, `checkpoint_decisions`. Migrations run on startup.
- **Fact bands**: confidence ≥ 0.85 is saved active, 0.60–0.85 pending for a person, below 0.60 dropped. Re-extraction never downgrades a fact, and rejected facts are never re-added. Set `APPROVED_OUTPUT_CONFIDENCE_CAP=0.8` to make a person confirm every fact worded by an agent once.

## Quality gates

Automated checks (`app/checks.py`) run before the QA Reviewer, and any blocker fails QA regardless of the model's verdict:

- health, medical and nutrition claims ("boosts immunity", "detox", "clinically proven")
- alcohol copy that appeals to minors, for breweries, wineries, bars and similar
- placeholders (`[TBD]`, lorem ipsum)
- invalid hex colors; WCAG contrast for text, muted text and accent buttons
- unsourced metrics and awards ("#1", "10x", "award-winning") as major issues
- default-AI indigo accents

The QA Reviewer adds judgment: consistency with brand facts and client answers, messaging that matches the strategy pillars, tone, and claims not supported by the deliverables.

## Design system export

The approved identity exports as an [OpenDesign](https://github.com/nexu-io/open-design) design-system package: `manifest.json` (`od-design-system-project/v1`), `DESIGN.md` and role-named `tokens.css` (`--bg`, `--fg`, `--accent`, ...). Drop the folder into OpenDesign's `design-systems/`, or hand it to any coding agent, and the client's website is built from the brand they signed off.

## Logging

Every line is JSON on stdout, tagged with `run_id`, `client_id`, `stage` and `agent` when they apply. Key events: `run.created`, `stage.started/completed/failed`, `agent.started/completed/failed` (latency, tokens, served model), `qa.reviewed`, `qa.routed_revision`, `qa.escalated`, `checkpoint.opened/decided`, `facts.saved`, `fact.dropped`, `untrusted.instruction_like`, `notify.needs_you`.

```bash
uvicorn app.main:app | jq 'select(.run_id=="<id>")'
```

## Tests and evaluations

```bash
pytest                                  # 73 offline tests, fake model, no services
INTEGRATION=1 pytest -m integration     # same engagement against real Redis + Postgres
python -m evals.run                     # live per-agent evals (calls the API, costs credits)
python -m evals.run --agent qa --trials 3
python -m evals.run --model <model-id>
```

The offline suite covers checkpoint order, change requests, reject, answers reaching later agents, QA routing and escalation, fact bands, facts feeding the next engagement, failure and retry, the decision audit, prompt-injection flagging, the HTTP API and the design-system export.

Each agent has graders in `evals/graders.py` (for example: research covers every named competitor; messaging maps to the strategy pillars and has no compliance blockers; identity meets contrast minimums; QA catches a planted health claim and a planted invented statistic; the extractor auto-saves stated facts and not speculation). `tests/test_graders.py` proves each grader passes the golden outputs and fails planted defects before it's trusted on live output. Live results are written to `evals/results/`.

## Before live clients

- Run `python -m evals.run --trials 3` and read the failures; this repo's live evals have not been run yet.
- Put the API behind authentication. It has none, and the console can approve work.
- The run lock is per process. Run a single API worker, or move the lock to Redis before scaling out.
- Read `docs/adr/` for why things are the way they are.

Credits for adapted ideas are in `THIRD_PARTY_NOTICES.md`.
