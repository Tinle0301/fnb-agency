"""Short-term session memory: the live state of a run, kept in Redis with a TTL.

A run's state (stage, every agent output so far, human feedback) and its event
log live here while the engagement is in progress. Nothing here is meant to
outlive the session; durable knowledge goes through the fact extractor into
Postgres (see facts.py).
"""

from __future__ import annotations

import json
from typing import Protocol

from app.schemas import Run, RunEvent, utcnow


class SessionStore(Protocol):
    async def save_run(self, run: Run) -> None: ...
    async def get_run(self, run_id: str) -> Run | None: ...
    async def append_event(self, run_id: str, event: RunEvent) -> None: ...
    async def get_events(self, run_id: str) -> list[RunEvent]: ...
    async def list_runs(self, limit: int = 100) -> list[Run]: ...
    async def close(self) -> None: ...


class RedisSessionStore:
    def __init__(self, url: str, ttl_seconds: int) -> None:
        import redis.asyncio as redis

        self._redis = redis.from_url(url, decode_responses=True)
        self._ttl = ttl_seconds

    @staticmethod
    def _run_key(run_id: str) -> str:
        return f"agency:run:{run_id}"

    @staticmethod
    def _events_key(run_id: str) -> str:
        return f"agency:run:{run_id}:events"

    _INDEX_KEY = "agency:runs"

    async def save_run(self, run: Run) -> None:
        run.updated_at = utcnow()
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(self._run_key(run.id), run.model_dump_json(), ex=self._ttl)
            pipe.zadd(self._INDEX_KEY, {run.id: run.created_at.timestamp()})
            await pipe.execute()

    async def get_run(self, run_id: str) -> Run | None:
        raw = await self._redis.get(self._run_key(run_id))
        return Run.model_validate_json(raw) if raw else None

    async def append_event(self, run_id: str, event: RunEvent) -> None:
        key = self._events_key(run_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.rpush(key, event.model_dump_json())
            pipe.expire(key, self._ttl)
            await pipe.execute()

    async def get_events(self, run_id: str) -> list[RunEvent]:
        raw = await self._redis.lrange(self._events_key(run_id), 0, -1)
        return [RunEvent.model_validate(json.loads(r)) for r in raw]

    async def list_runs(self, limit: int = 100) -> list[Run]:
        ids = await self._redis.zrevrange(self._INDEX_KEY, 0, limit - 1)
        if not ids:
            return []
        raws = await self._redis.mget([self._run_key(i) for i in ids])
        expired = [i for i, raw in zip(ids, raws) if raw is None]
        if expired:
            await self._redis.zrem(self._INDEX_KEY, *expired)
        return [Run.model_validate_json(raw) for raw in raws if raw]

    async def close(self) -> None:
        await self._redis.aclose()


class InMemorySessionStore:
    """Same interface without Redis, for tests and `AGENCY_STORAGE=memory` demos."""

    def __init__(self) -> None:
        self._runs: dict[str, str] = {}
        self._events: dict[str, list[RunEvent]] = {}

    async def save_run(self, run: Run) -> None:
        run.updated_at = utcnow()
        self._runs[run.id] = run.model_dump_json()

    async def get_run(self, run_id: str) -> Run | None:
        raw = self._runs.get(run_id)
        return Run.model_validate_json(raw) if raw else None

    async def append_event(self, run_id: str, event: RunEvent) -> None:
        self._events.setdefault(run_id, []).append(event)

    async def get_events(self, run_id: str) -> list[RunEvent]:
        return list(self._events.get(run_id, []))

    async def list_runs(self, limit: int = 100) -> list[Run]:
        runs = [Run.model_validate_json(raw) for raw in self._runs.values()]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)[:limit]

    async def close(self) -> None:
        pass
