"""Tell a person when a run needs them.

When a run opens a checkpoint, escalates QA, or fails, a JSON message is POSTed to
NOTIFY_WEBHOOK_URL (a Slack incoming webhook works as-is). Without a URL, it is only logged.
Delivery is best-effort: a notification failure never fails the run.
"""

from __future__ import annotations

import httpx

from app.logging_setup import get_logger

log = get_logger(__name__)


class Notifier:
    def __init__(self, webhook_url: str | None = None, public_base_url: str = "") -> None:
        self.webhook_url = webhook_url
        self.public_base_url = public_base_url.rstrip("/")
        self.sent: list[dict] = []  # kept for tests and the dev console

    async def needs_you(self, *, run_id: str, client_name: str, reason: str) -> None:
        link = f"{self.public_base_url}/runs/{run_id}" if self.public_base_url else f"run {run_id}"
        message = {"text": f"{client_name}: {reason} ({link})", "run_id": run_id, "reason": reason}
        self.sent.append(message)
        log.info("notify.needs_you", run_id=run_id, reason=reason)
        if not self.webhook_url:
            return
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.post(self.webhook_url, json=message)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("notify.failed", run_id=run_id, error=str(exc))
