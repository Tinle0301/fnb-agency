# Two memory layers: Redis for the session, Postgres for brand facts

A run's working state (every draft, feedback, events) is large, short-lived and rewritten often, so it lives in Redis with a TTL. What we learn about a client must outlive any one run and be auditable, so only extracted brand facts and checkpoint decisions go to Postgres. Agents never read old sessions; they read active brand facts.
