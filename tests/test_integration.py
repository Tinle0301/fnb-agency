"""The same engagement against real Redis and Postgres.

Skipped unless both are reachable. With docker compose up:

    INTEGRATION=1 pytest -m integration
"""

from __future__ import annotations

import os
import uuid

import pytest

from app.config import Settings
from app.memory.facts import PostgresBrandMemory
from app.memory.session import RedisSessionStore
from app.orchestrator import Orchestrator, current_checkpoint
from app.schemas import Decision, FactStatus, RunStatus
from evals import fixtures as fx

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.skipif(not os.getenv("INTEGRATION"), reason="set INTEGRATION=1 with Redis and Postgres running"),
]


async def test_engagement_persists_across_redis_and_postgres(llm):
    settings = Settings.from_env()
    sessions = RedisSessionStore(settings.redis_url, 600)
    memory = PostgresBrandMemory(settings.database_url)
    await memory.open()
    client_id = f"it-{uuid.uuid4().hex[:8]}"
    brief = fx.BREWERY_BRIEF.model_copy(update={"client_id": client_id})
    try:
        orch = Orchestrator(llm, sessions, memory, settings)
        run = await orch.start_run(brief)
        run = await orch.advance(run.id)
        while run.status is RunStatus.awaiting_approval:
            run = await orch.decide(run.id, checkpoint=current_checkpoint(run), decision=Decision.approve, actor="it")
            run = await orch.advance(run.id)
        assert run.status is RunStatus.completed

        # A fresh store instance sees the run (Redis) and the facts (Postgres).
        reread = await RedisSessionStore(settings.redis_url, 600).get_run(run.id)
        assert reread.status is RunStatus.completed
        assert any(r.id == run.id for r in await sessions.list_runs())
        active = await memory.get_facts(client_id, FactStatus.active)
        pending = await memory.get_facts(client_id, FactStatus.pending)
        assert len(active) == 2 and len(pending) == 1

        # Re-saving the same facts does not duplicate them.
        await memory.save_facts(active)
        assert len(await memory.get_facts(client_id, FactStatus.active)) == 2

        confirmed = await memory.set_fact_status(pending[0].id, FactStatus.active)
        assert confirmed.status is FactStatus.active
    finally:
        await sessions.close()
        await memory.close()
