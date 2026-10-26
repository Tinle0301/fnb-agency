-- Long-term brand memory.

CREATE TABLE IF NOT EXISTS clients (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS brand_facts (
    id             BIGSERIAL PRIMARY KEY,
    client_id      TEXT NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    category       TEXT NOT NULL,
    statement      TEXT NOT NULL,
    -- Normalised statement, used to de-duplicate facts across sessions.
    statement_key  TEXT NOT NULL,
    source         TEXT NOT NULL,
    evidence       TEXT NOT NULL DEFAULT '',
    confidence     REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    status         TEXT NOT NULL CHECK (status IN ('active', 'pending', 'rejected')),
    source_run_id  TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (client_id, category, statement_key)
);

CREATE INDEX IF NOT EXISTS brand_facts_client_status ON brand_facts (client_id, status);

-- Audit trail of every human checkpoint decision.
CREATE TABLE IF NOT EXISTS checkpoint_decisions (
    id          BIGSERIAL PRIMARY KEY,
    run_id      TEXT NOT NULL,
    client_id   TEXT NOT NULL,
    checkpoint  TEXT NOT NULL,
    decision    TEXT NOT NULL,
    feedback    TEXT NOT NULL DEFAULT '',
    actor       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS checkpoint_decisions_run ON checkpoint_decisions (run_id);
