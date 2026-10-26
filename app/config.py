"""Runtime settings, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    # Models. The six agency agents share one model; the fact extractor uses a smaller one.
    # No defaults: set AGENCY_MODEL and EXTRACTOR_MODEL in .env.
    agent_model: str = ""
    agent_effort: str = "high"
    extractor_model: str = ""
    extractor_effort: str = "low"
    # Server-side refusal fallback. Turn on only for a model that supports it.
    use_refusal_fallbacks: bool = False

    # Storage. "redis+postgres" for real runs, "memory" for local demos and tests.
    storage: str = "redis+postgres"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://agency:agency@localhost:5432/agency"
    session_ttl_seconds: int = 7 * 24 * 3600

    # Fact extraction confidence bands.
    #   >= auto_save  -> saved as an active brand fact
    #   >= review     -> saved as "pending" for a human to confirm
    #   below review  -> dropped (logged, never persisted)
    fact_auto_save_threshold: float = 0.85
    fact_review_threshold: float = 0.60
    # Optional ceiling for facts sourced from agent-written (approved) deliverables.
    approved_output_confidence_cap: float | None = None

    # Human checkpoints. The pipeline pauses after each listed stage.
    checkpoints: frozenset[str] = field(
        default_factory=lambda: frozenset({"research", "strategy", "final"})
    )
    # How many times the Report Producer may revise after a QA failure before escalating.
    max_qa_revisions: int = 2

    # Where "a run needs you" notifications go (e.g. a Slack incoming webhook), and the
    # base URL used to link back to a run.
    notify_webhook_url: str | None = None
    public_base_url: str = "http://localhost:8000"

    # Canned outputs instead of the model API (see app/demo.py).
    demo: bool = False

    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        checkpoints = _env("AGENCY_CHECKPOINTS", "research,strategy,final")
        return cls(
            agent_model=_env("AGENCY_MODEL", cls.agent_model),
            agent_effort=_env("AGENCY_EFFORT", cls.agent_effort),
            extractor_model=_env("EXTRACTOR_MODEL", cls.extractor_model),
            extractor_effort=_env("EXTRACTOR_EFFORT", cls.extractor_effort),
            use_refusal_fallbacks=_env("USE_REFUSAL_FALLBACKS", "false").lower() == "true",
            storage=_env("AGENCY_STORAGE", cls.storage),
            redis_url=_env("REDIS_URL", cls.redis_url),
            database_url=_env("DATABASE_URL", cls.database_url),
            session_ttl_seconds=int(_env("SESSION_TTL_SECONDS", str(cls.session_ttl_seconds))),
            fact_auto_save_threshold=float(
                _env("FACT_AUTO_SAVE_THRESHOLD", str(cls.fact_auto_save_threshold))
            ),
            fact_review_threshold=float(
                _env("FACT_REVIEW_THRESHOLD", str(cls.fact_review_threshold))
            ),
            approved_output_confidence_cap=(
                float(os.environ["APPROVED_OUTPUT_CONFIDENCE_CAP"])
                if os.getenv("APPROVED_OUTPUT_CONFIDENCE_CAP")
                else None
            ),
            # "final" is always a checkpoint: nothing reaches a client without a person.
            checkpoints=frozenset(
                {c.strip() for c in checkpoints.split(",") if c.strip()} | {"final"}
            ),
            max_qa_revisions=int(_env("MAX_QA_REVISIONS", str(cls.max_qa_revisions))),
            notify_webhook_url=os.getenv("NOTIFY_WEBHOOK_URL") or None,
            public_base_url=_env("PUBLIC_BASE_URL", cls.public_base_url),
            demo=_env("AGENCY_DEMO", "0").lower() in ("1", "true"),
            log_level=_env("LOG_LEVEL", cls.log_level),
        )
