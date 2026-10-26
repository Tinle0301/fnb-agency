# F&B Virtual Agency

A brand agency for food and beverage clients, run by six AI specialists and steered by you from one dashboard. Give it a client brief and it returns research, a brand strategy, messaging, a visual identity, a client-ready report and a design system your web developer can build from. Nothing moves forward until a person approves it.

| Agent | What it hands you |
|---|---|
| Research Analyst | Market, audience insights, competitors, trends, regulatory notes, questions for the client |
| Brand Strategist | Positioning, brand pillars, personality, promise |
| Messaging Lead | Taglines, voice, key messages, menu and social copy |
| Identity Direction | Palette, design tokens, typography, logo direction |
| Report Producer | The client-facing brand report |
| QA Reviewer | A score and a list of issues, sent back to whichever agent owns them |

## 1. Start the dashboard

You need Python 3.11 or newer.

**Try it first in demo mode.** No API key and no databases. Every brief returns the same sample (Harbor Hops Brewing), so use it to learn the screens, not to judge the work.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
AGENCY_DEMO=1 AGENCY_STORAGE=memory uvicorn app.main:app
```

**Run it for real.** This also needs Docker for Redis and Postgres.

```bash
cp .env.example .env      # add your API key and the two model IDs
docker compose up -d      # Redis (session memory) + Postgres (brand memory)
uvicorn app.main:app
```

Open **http://localhost:8000**. The header says "Demo mode" when you are in demo mode, and shows which storage the dashboard is using.

## 2. Find your way around

The dark bar under the header has four tabs:

- **Overview**: every engagement, sorted into what needs you.
- **New engagement**: the client brief form.
- **Brand memory**: what the agency has learned about each client.
- **How it works**: the pipeline and the quality rules, for new team members.

A number next to a tab shows how much is waiting for you: engagements to review next to Overview, facts to confirm next to Brand memory. The dashboard refreshes on its own every few seconds, and pauses while you are typing.

## 3. Start an engagement

1. Click **New engagement**.
2. Fill in the brief: client name, business type, location, audience, goals, constraints, competitors and any notes. Click **Fill with sample brief** to see a complete one.
3. The client ID is filled in from the name. Keep it the same for every engagement with the same client, because that is how brand memory follows the client.
4. Click **Start engagement**. You land on the engagement page, and the Research Analyst starts straight away.

Write the brief the way the client said it. Text that reads like instructions to the AI ("ignore your rules…") is flagged and treated as client content, never as commands.

## 4. Follow an engagement

Each engagement page has:

- **The pipeline**: one step per agent and per checkpoint (✋). Green is done, blue is working, brown is waiting for you, red is failed.
- **A banner** that says what is happening now and what, if anything, you need to do.
- **Deliverables**: the work so far, one tab per deliverable.
- **Downloads**: the brand report (Markdown) and the design system (.zip), once they exist.
- **Brief** and **Activity**: the original brief, the client's answers, and a timestamped log of every step.

If an agent fails, the banner says why. Click **Retry stage** to run that stage again.

## 5. Review at each checkpoint

When a checkpoint opens, the engagement moves to **Needs you** on the Overview and a review card appears at the top of the page. You have three choices:

- **Approve and continue**: the next agents start.
- **Request changes**: write what to change in **Feedback** (it is required). The stage runs again with your note.
- **Reject**: the engagement stops.

The checkpoints, in order:

1. **Research review.** Read the findings and answer the **Questions for the client**. Each comes with a recommended answer; change it to what the client actually said. Every later agent sees these answers, and they are saved as facts about the client.
2. **Strategy review.** Check the positioning and pillars. Everything after this point is built on them.
3. **Final sign-off.** Messaging and identity run side by side, then the Report Producer writes the report and QA reviews everything. Read the **Report**, **QA**, **Messaging** and **Identity** tabs. The Identity tab shows the palette, a live preview built from the design tokens and the contrast ratio of every text pair.

If QA finds a problem, the issue goes back to the agent that owns it (a weak tagline to the Messaging Lead, a contrast failure to Identity Direction) and the report is rebuilt. If QA still fails after the set number of revisions, the final checkpoint opens with a red **QA did not pass** banner, so you decide with the issues in front of you.

## 6. Hand off the work

After final sign-off, the **Deliverables** card gives you:

- **Brand report (Markdown)**: ready to paste into a deck or doc for the client.
- **Design system (.zip)**: `DESIGN.md`, `tokens.css` and `manifest.json` in the [OpenDesign](https://github.com/nexu-io/open-design) format. Give it to the person or tool building the client's website so the site uses exactly the brand the client signed off.

## 7. Keep brand memory accurate

When you give final sign-off, the agency pulls lasting facts out of the engagement ("founders are former lobstermen", "never use anchors") and gives each one a confidence score.

- **High confidence** facts are saved as **active**. Every agent sees them in the client's next engagement.
- **Medium confidence** facts are saved as **pending** and wait for you.
- **Low confidence** facts are dropped.

Open **Brand memory**, pick a client, and use the **Pending** tab to **Confirm** or **Reject** each fact. A rejected fact is never added back automatically. The **Active** and **Rejected** tabs show what the agency currently knows and what you ruled out.

## 8. Settings you may want

Set these in `.env`:

| Setting | What it does |
|---|---|
| `AGENCY_CHECKPOINTS` | Which reviews open, for example `research,strategy,final`. Add `creative` to review messaging and identity before the report. Final sign-off is always on. |
| `MAX_QA_REVISIONS` | How many times QA can send work back before it escalates to you. Default 2. |
| `NOTIFY_WEBHOOK_URL` | A Slack incoming webhook (or any webhook) to ping you when an engagement needs you. |
| `PUBLIC_BASE_URL` | The dashboard's address, used for links in those pings. |
| `FACT_AUTO_SAVE_THRESHOLD`, `FACT_REVIEW_THRESHOLD` | The confidence bands for brand memory (defaults 0.85 and 0.60). |
| `APPROVED_OUTPUT_CONFIDENCE_CAP` | Set to `0.8` to make you confirm every fact the agents worded themselves at least once. |

`.env.example` lists every setting.

## Before you use it with real clients

- The dashboard has no login, and anyone who can open it can approve work. Keep it on your own machine or put it behind authentication.
- Run the agent evaluations and read the failures: `python -m evals.run --trials 3`. They call the API and cost credits.
- Run one API worker. The lock that stops two people approving the same step at once is per process.

## For developers

```bash
pytest                                  # offline tests, fake model, no services
INTEGRATION=1 pytest -m integration     # against real Redis and Postgres
python -m evals.run --agent qa          # live evaluation of one agent
```

The API behind the dashboard is documented at http://localhost:8000/docs. Code layout, logging and design decisions are in `AGENTS.md`, `GLOSSARY.md` and `docs/adr/`. Credits for adapted ideas are in `THIRD_PARTY_NOTICES.md`.
