"""Anthropic (Claude / Claude Code) admin usage collector.

Polls the Anthropic Admin API ``/v1/organizations/usage_report/messages``
endpoint for aggregated token usage grouped by model, and normalizes each
(model, bucket) into a record that the reconciliation service upserts into
``enriched_request``.

Requires an Admin API key (``sk-ant-admin01-...``) sent via the ``x-api-key``
header, plus ``anthropic-version: 2023-06-01``. Set
``GLM_MONITOR_ANTHROPIC_ENABLED`` and ``GLM_MONITOR_ANTHROPIC_API_KEY`` to
activate. Usage data lags ~5 minutes behind real request completion, so the
poller re-queries a trailing window and upserts (partial buckets fill in).
"""
import logging
from datetime import datetime, timezone
from dateutil.parser import isoparse
from typing import Any, Optional

import httpx

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

_PROVIDER = "anthropic"
_SOURCE = "anthropic_admin"
_ANTHROPIC_VERSION = "2023-06-01"


def _parse_iso(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        dt = isoparse(str(value))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _cache_creation_total(cache: Any) -> int:
    """Anthropic splits cache-creation tokens into 5m / 1h ephemeral buckets."""
    if not isinstance(cache, dict):
        return 0
    return int(cache.get("ephemeral_5m_input_tokens") or 0) + int(
        cache.get("ephemeral_1h_input_tokens") or 0
    )


def _normalize_bucket(bucket: dict) -> list[dict]:
    out: list[dict] = []
    start = _parse_iso(bucket.get("starting_at"))
    end = _parse_iso(bucket.get("ending_at"))
    for result in bucket.get("results", []) or []:
        if not isinstance(result, dict):
            continue
        model = result.get("model") or "unknown"
        uncached = int(result.get("uncached_input_tokens") or 0)
        cache_read = int(result.get("cache_read_input_tokens") or 0)
        cache_create = _cache_creation_total(result.get("cache_creation"))
        # Total input consumed = uncached + cache read + cache written.
        input_tokens = uncached + cache_read + cache_create
        output_tokens = int(result.get("output_tokens") or 0)
        total = input_tokens + output_tokens
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
                "num_requests": None,  # Anthropic usage_report has no request count.
                "metadata": {
                    "uncached_input_tokens": uncached,
                    "cache_read_input_tokens": cache_read,
                    "cache_creation_input_tokens": cache_create,
                    "output_tokens": output_tokens,
                    "bucket": "anthropic_admin",
                },
            }
        )
    return out


class AnthropicCollector(BaseCollector):
    def __init__(self):
        super().__init__("anthropic")
        self.last_success: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.last_failure: Optional[datetime] = None
        self.consecutive_failures = 0
        self._client: Optional[httpx.AsyncClient] = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.anthropic_base_url,
                headers={
                    "x-api-key": settings.anthropic_api_key.get_secret_value(),
                    "anthropic-version": _ANTHROPIC_VERSION,
                    "Accept": "application/json",
                },
                timeout=15.0,
            )
        return self._client

    async def start(self) -> None:
        if not settings.anthropic_enabled:
            logger.info("AnthropicCollector is disabled in settings.")
            return
        self._ensure_client()
        self.is_running = True
        logger.info("AnthropicCollector started (polling driven by scheduler).")

    async def stop(self) -> None:
        self.is_running = False
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_usage(self, start: datetime, end: datetime) -> list[dict]:
        """Fetch messages usage for [start, end) grouped by model."""
        client = self._ensure_client()
        params: list[tuple[str, str]] = [
            ("starting_at", start.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("ending_at", end.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("bucket_width", "1h"),
            ("group_by[]", "model"),
            ("limit", "168"),  # one week of hourly buckets is the documented max.
        ]
        records: list[dict] = []
        try:
            for _ in range(20):
                resp = await client.get(
                    "/v1/organizations/usage_report/messages", params=params
                )
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
            logger.error("Anthropic usage fetch failed: %s", exc)
            raise

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.consecutive_failures == 0,
            "enabled": settings.anthropic_enabled,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
        }
