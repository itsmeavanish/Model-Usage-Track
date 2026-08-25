"""Z.ai admin usage collector (per-model token usage from the monitor API).

Polls the ``/api/monitor/usage/model-usage`` endpoint — the same undocumented
API the Z.ai web dashboard and the official ``glm-plan-usage`` plugin call —
for aggregated token usage grouped by model in hourly buckets. Unlike the
proxy, this sees **Coding Plan subscription** traffic too, because Z.ai
aggregates it server-side per model per hour. Only per-request capture still
requires routing a prepaid key through the proxy.

Two quirks learned from the official plugin (zai-coding-plugins) and verified
against the live API:

* Auth is the RAW key in the ``Authorization`` header — no "Bearer" prefix.
* Time windows are naive wall-clock strings and the API labels its hourly
  buckets (``x_time``) in whatever zone the request used. We send UTC and
  parse the labels back as UTC, which keeps bucket ids stable across polls.

Each (model, hour) is normalized into one record that the reconciliation
service upserts into ``enriched_request`` with ``provider=zai`` /
``source=zai_admin`` — the same flow as the OpenAI/Anthropic admin pollers.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

_PROVIDER = "zai"
_SOURCE = "zai_admin"


def _format_window(dt: datetime) -> str:
    """Aware datetime -> naive UTC string, e.g. '2026-08-21 17:00:00'."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _parse_bucket_label(value) -> Optional[datetime]:
    """Bucket label '2026-08-21 17:00' -> aware UTC datetime (labels mirror
    the timezone we sent the window in, which is always UTC here)."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _normalize_response(data: dict) -> list[dict]:
    """Flatten one model-usage response into per-(model, hour) records."""
    out: list[dict] = []
    x_time = data.get("x_time") or []
    for entry in data.get("modelDataList") or []:
        if not isinstance(entry, dict):
            continue
        # Lowercase so admin rows group with proxy rows ("GLM-5.3" vs "glm-5.3").
        model = str(entry.get("modelName") or "unknown").strip().lower()
        tokens = entry.get("tokensUsage") or []
        calls = entry.get("modelCallCount") or []
        for i, label in enumerate(x_time):
            total = int(tokens[i]) if i < len(tokens) else 0
            if total <= 0:
                continue
            start = _parse_bucket_label(label)
            if start is None:
                continue
            num_req = int(calls[i]) if i < len(calls) and calls[i] else None
            out.append(
                {
                    "provider": _PROVIDER,
                    "source": _SOURCE,
                    "model": model,
                    "bucket_start": start,
                    "bucket_end": start + timedelta(hours=1),
                    # The endpoint reports a single combined figure per bucket;
                    # the prompt/completion split is not available.
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": total,
                    "num_requests": num_req,
                    "metadata": {"bucket": "zai_admin", "split_unavailable": True},
                }
            )
    return out


class ZaiAdminCollector(BaseCollector):
    def __init__(self):
        super().__init__("zai_admin")
        self.last_success: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.last_failure: Optional[datetime] = None
        self.consecutive_failures = 0
        self._client: Optional[httpx.AsyncClient] = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.zai_base_url,
                headers={
                    # Raw token, no Bearer — how Z.ai's own plugin authenticates.
                    "Authorization": settings.zai_api_key.get_secret_value(),
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en",
                },
                timeout=15.0,
            )
        return self._client

    async def start(self) -> None:
        if not settings.zai_admin_enabled:
            logger.info("ZaiAdminCollector is disabled in settings.")
            return
        self.is_running = True
        logger.info("ZaiAdminCollector started (polling driven by scheduler).")

    async def stop(self) -> None:
        self.is_running = False
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_usage(self, start: datetime, end: datetime) -> list[dict]:
        """Fetch per-model hourly usage for [start, end).

        Returns a flat list of normalized per-(model, bucket) records.
        """
        client = self._ensure_client()
        try:
            resp = await client.get(
                settings.zai_model_usage_endpoint,
                params={
                    "startTime": _format_window(start),
                    "endTime": _format_window(end),
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 200:
                raise ValueError(f"API returned error code: {data.get('code')}")

            records = _normalize_response(data.get("data") or {})
            self.last_success = datetime.now(timezone.utc)
            self.consecutive_failures = 0
            self.last_error = None
            return records
        except Exception as exc:
            self.consecutive_failures += 1
            self.last_error = str(exc)
            self.last_failure = datetime.now(timezone.utc)
            logger.error("Z.ai model-usage fetch failed: %s", exc)
            raise

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.consecutive_failures == 0,
            "enabled": settings.zai_admin_enabled,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
        }
