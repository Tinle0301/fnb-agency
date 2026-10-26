"""Long-term brand memory in PostgreSQL: durable brand facts and the approval audit trail.

Facts arrive from the fact extractor with a status already decided by confidence
band (active / pending). Re-extracting a known fact never downgrades it, and a
fact a person rejected is never brought back automatically.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from app.schemas import BrandFact, FactStatus

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def statement_key(statement: str) -> str:
    text = re.sub(r"[^\w\s#]", "", statement.lower())
    return re.sub(r"\s+", " ", text).strip()


class BrandMemory(Protocol):
    async def ensure_client(self, client_id: str, name: str) -> None: ...
    async def get_facts(self, client_id: str, status: FactStatus | None = None) -> list[BrandFact]: ...
    async def save_facts(self, facts: list[BrandFact]) -> None: ...
    async def set_fact_status(self, fact_id: int, status: FactStatus) -> BrandFact | None: ...
    async def record_decision(
        self, run_id: str, client_id: str, checkpoint: str, decision: str, feedback: str, actor: str
    ) -> None: ...
    async def close(self) -> None: ...


def _merge_status(existing: FactStatus, incoming: FactStatus) -> FactStatus:
    if existing in (FactStatus.active, FactStatus.rejected):
        return existing
    return incoming


class PostgresBrandMemory:
    def __init__(self, database_url: str) -> None:
        from psycopg_pool import AsyncConnectionPool

        self._pool = AsyncConnectionPool(database_url, open=False, min_size=1, max_size=5)

    async def open(self) -> None:
        await self._pool.open()
        await self.migrate()

    async def migrate(self) -> None:
        async with self._pool.connection() as conn:
            for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                await conn.execute(path.read_text())

    async def ensure_client(self, client_id: str, name: str) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "INSERT INTO clients (id, name) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                (client_id, name),
            )

    async def get_facts(self, client_id: str, status: FactStatus | None = None) -> list[BrandFact]:
        query = (
            "SELECT id, client_id, category, statement, source, evidence, confidence, status, "
            "source_run_id, created_at FROM brand_facts WHERE client_id = %s"
        )
        params: list = [client_id]
        if status is not None:
            query += " AND status = %s"
            params.append(status.value)
        query += " ORDER BY category, confidence DESC"
        async with self._pool.connection() as conn:
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()
        return [_row_to_fact(r) for r in rows]

    async def save_facts(self, facts: list[BrandFact]) -> None:
        if not facts:
            return
        async with self._pool.connection() as conn:
            async with conn.transaction():
                for f in facts:
                    await conn.execute(
                        """
                        INSERT INTO brand_facts (client_id, category, statement, statement_key, source,
                                                 evidence, confidence, status, source_run_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (client_id, category, statement_key) DO UPDATE SET
                            confidence = GREATEST(brand_facts.confidence, EXCLUDED.confidence),
                            status = CASE WHEN brand_facts.status IN ('active', 'rejected')
                                          THEN brand_facts.status ELSE EXCLUDED.status END,
                            updated_at = now()
                        """,
                        (
                            f.client_id,
                            f.category,
                            f.statement,
                            statement_key(f.statement),
                            f.source,
                            f.evidence,
                            f.confidence,
                            f.status.value,
                            f.source_run_id,
                        ),
                    )

    async def set_fact_status(self, fact_id: int, status: FactStatus) -> BrandFact | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "UPDATE brand_facts SET status = %s, updated_at = now() WHERE id = %s "
                "RETURNING id, client_id, category, statement, source, evidence, confidence, status, "
                "source_run_id, created_at",
                (status.value, fact_id),
            )
            row = await cur.fetchone()
        return _row_to_fact(row) if row else None

    async def record_decision(
        self, run_id: str, client_id: str, checkpoint: str, decision: str, feedback: str, actor: str
    ) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                "INSERT INTO checkpoint_decisions (run_id, client_id, checkpoint, decision, feedback, actor) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (run_id, client_id, checkpoint, decision, feedback, actor),
            )

    async def close(self) -> None:
        await self._pool.close()


def _row_to_fact(row: tuple) -> BrandFact:
    return BrandFact(
        id=row[0],
        client_id=row[1],
        category=row[2],
        statement=row[3],
        source=row[4],
        evidence=row[5],
        confidence=row[6],
        status=FactStatus(row[7]),
        source_run_id=row[8],
        created_at=row[9],
    )


class InMemoryBrandMemory:
    """Same semantics as PostgresBrandMemory, for tests and `AGENCY_STORAGE=memory` demos."""

    def __init__(self) -> None:
        self.clients: dict[str, str] = {}
        self.facts: dict[int, BrandFact] = {}
        self.decisions: list[dict] = []
        self._next_id = 1

    async def ensure_client(self, client_id: str, name: str) -> None:
        self.clients[client_id] = name

    async def get_facts(self, client_id: str, status: FactStatus | None = None) -> list[BrandFact]:
        facts = [
            f
            for f in self.facts.values()
            if f.client_id == client_id and (status is None or f.status == status)
        ]
        return sorted(facts, key=lambda f: (f.category, -f.confidence))

    async def save_facts(self, facts: list[BrandFact]) -> None:
        for fact in facts:
            key = (fact.client_id, fact.category, statement_key(fact.statement))
            existing = next(
                (
                    f
                    for f in self.facts.values()
                    if (f.client_id, f.category, statement_key(f.statement)) == key
                ),
                None,
            )
            if existing:
                existing.confidence = max(existing.confidence, fact.confidence)
                existing.status = _merge_status(existing.status, fact.status)
                continue
            stored = fact.model_copy(update={"id": self._next_id})
            self.facts[self._next_id] = stored
            self._next_id += 1

    async def set_fact_status(self, fact_id: int, status: FactStatus) -> BrandFact | None:
        fact = self.facts.get(fact_id)
        if fact:
            fact.status = status
        return fact

    async def record_decision(
        self, run_id: str, client_id: str, checkpoint: str, decision: str, feedback: str, actor: str
    ) -> None:
        self.decisions.append(
            {
                "run_id": run_id,
                "client_id": client_id,
                "checkpoint": checkpoint,
                "decision": decision,
                "feedback": feedback,
                "actor": actor,
            }
        )

    async def close(self) -> None:
        pass
