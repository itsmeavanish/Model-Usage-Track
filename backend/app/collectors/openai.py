"""OpenAI (ChatGPT / GPT) admin usage collector.

Polls the OpenAI Admin API ``/v1/organization/usage/completions`` endpoint for
aggregated token usage grouped by model, and normalizes each (model, bucket)
into a record that the reconciliation service upserts into ``enriched_request``.

Requires an Admin API key (``sk-admin-...``). Set ``GLM_MONITOR_OPENAI_ENABLED``
and ``GLM_MONITOR_OPENAI_API_KEY`` to activate. The poll itself is driven by the
APScheduler job wired in main.py (mirrors the Z.ai official quota poller).
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

_PROVIDER = "openai"
_SOURCE = "openai_admin"


def _parse_bucket_ts(value: Any) -> Optional[datetime]:
    """OpenAI reports bucket start/end as unix seconds (number)."""
    if value is None:
        return None
    try:
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError):
        return None
    return dt


def _normalize_bucket(bucket: dict) -> list[dict]:
    """Flatten one OpenAI usage bucket into per-model aggregate records."""
    out: list[dict] = []
    start = _parse_bucket_ts(bucket.get("start_time"))
    end = _parse_bucket_ts(bucket.get("end_time"))
    for result in bucket.get("results", []) or []:
        if not isinstance(result, dict):
            continue
        model = result.get("model") or "unknown"
        input_tokens = int(result.get("input_tokens") or 0)
        output_tokens = int(result.get("output_tokens") or 0)
        # Drop no-op buckets (e.g. cached-only with zero billable tokens).
        total = int(result.get("total_tokens") or (input_tokens + output_tokens))
        if total <= 0:
            continue
        out.append(
            {
                "provider": _PROVIDER,
                "source": _SOURCE,
                "model": model,
                "bucket_start": start,
                "bucket_end": end,
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": total,
                "num_requests": int(result.get("num_model_requests") or 0) or None,
                "metadata": {
                    "input_cached_tokens": result.get("input_cached_tokens"),
                    "num_model_requests": result.get("num_model_requests"),
                    "bucket": "openai_admin",
                },
            }
        )
    return out


class OpenAICollector(BaseCollector):
    def __init__(self):
        super().__init__("openai")
        self.last_success: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.last_failure: Optional[datetime] = None
        self.consecutive_failures = 0
        self._client: Optional[httpx.AsyncClient] = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.openai_base_url,
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                    "Accept": "application/json",
                },
                timeout=15.0,
            )
        return self._client

    async def start(self) -> None:
        if not settings.openai_enabled:
            logger.info("OpenAICollector is disabled in settings.")
            return
        # Client is created lazily so importing the module never requires a key.
        self._ensure_client()
        self.is_running = True
        logger.info("OpenAICollector started (polling driven by scheduler).")

    async def stop(self) -> None:
        self.is_running = False
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_usage(self, start: datetime, end: datetime) -> list[dict]:
        """Fetch completions usage for [start, end) grouped by model.

        Returns a flat list of normalized per-(model, bucket) records.
        """
        client = self._ensure_client()
        params: list[tuple[str, str]] = [
            ("start_at", start.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("end_at", end.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("bucket_width", "1h"),
            ("limit", "1000"),
            ("group_by[]", "model"),
        ]
        records: list[dict] = []
        try:
            for _ in range(20):  # hard cap on pagination depth
                resp = await client.get("/v1/organization/usage/completions", params=params)
                resp.raise_for_status()
                data = resp.json()
                for bucket in data.get("data", []) or []:
                    records.extend(_normalize_bucket(bucket))

                if data.get("has_more") and data.get("next_page"):
                    params = [(k, v) for k, v in params if k != "page"]
                    params.append(("page", str(data["next_page"])))
                    continue
                break

            self.last_success = datetime.now(timezone.utc)
            self.consecutive_failures = 0
            self.last_error = None
            return records
        except Exception as exc:
            self.consecutive_failures += 1
            self.last_error = str(exc)
            self.last_failure = datetime.now(timezone.utc)
            logger.error("OpenAI usage fetch failed: %s", exc)
            raise

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.consecutive_failures == 0,
            "enabled": settings.openai_enabled,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
        }
