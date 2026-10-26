# Working on this repo

- Read `GLOSSARY.md` and use its terms in code, tests and prompts. Decisions are in `docs/adr/`.
- Run `pytest` before and after a change; it runs offline with a fake model. `INTEGRATION=1 pytest -m integration` needs `docker compose up`.
- A prompt change is a behaviour change: run `python -m evals.run --agent <name>` (costs API credits) and compare with the last result in `evals/results/`.
- A new rule that can be checked in code goes in `app/checks.py` with a test, not only in a prompt.
- Agent output models in `app/schemas.py` are sent as structured-output schemas: plain types, every field required, no numeric bounds.
