from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.request_repository import RequestRepository
from app.models.enriched_request import EnrichedRequest
from app.core.events import event_bus
from app.config import settings
from datetime import datetime, timezone
from dateutil.parser import isoparse
import uuid
import logging

logger = logging.getLogger(__name__)


def _parse_timestamp(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        dt = isoparse(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _aggregate_request_id(provider: str, model: str, bucket_start: datetime) -> str:
    """Deterministic id for an admin-API usage bucket → idempotent upserts."""
    ts = bucket_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{provider}:{model}:{ts}"

class ReconciliationService:
    def __init__(self, db: AsyncSession):
        self.repo = RequestRepository(db)

    async def ingest_request(self, request_data: dict) -> EnrichedRequest:
        """
        Ingest a request from an enrichment collector (proxy, log, webhook).
        Deduplicates against existing requests to prevent double counting.
        """
        request_id = request_data.get("request_id")
        if not request_id:
            # Generate a local ID if source didn't provide one
            request_id = f"local_{uuid.uuid4().hex}"
            request_data["request_id"] = request_id

        # 1. Exact match by request_id
        existing = await self.repo.get_by_id(request_id)
        if existing:
            return await self._merge_requests(existing, request_data)

        # 2. Fuzzy match (same model, same tokens, within 2 seconds)
        ts_dt = _parse_timestamp(request_data.get("timestamp"))
        total_tokens = request_data.get("total_tokens", 0)
        model = request_data.get("model")

        if ts_dt and total_tokens > 0 and model:
            # We would normally do a fuzzy query here:
            # e.g., timestamp between (timestamp - 2s) and (timestamp + 2s)
            # For simplicity, we just insert as new if no exact request_id match.
            # In a full implementation, we'd add fuzzy query to repository.
            pass

        # Insert new
        new_req = EnrichedRequest(
            request_id=request_id,
            source=request_data.get("source"),
            provider=request_data.get("provider") or settings.default_provider,
            timestamp=ts_dt,
            model=model,
            prompt_tokens=request_data.get("prompt_tokens", 0),
            completion_tokens=request_data.get("completion_tokens", 0),
            total_tokens=total_tokens,
            latency_ms=request_data.get("latency_ms", 0.0),
            status_code=request_data.get("status_code", 200),
            application=request_data.get("application"),
            project=request_data.get("project"),
            machine=request_data.get("machine"),
            user_id=request_data.get("user_id"),
            req_metadata=request_data.get("metadata", {}),
            is_streaming=request_data.get("is_streaming", False),
            is_reconciled=False
        )
        
        saved = await self.repo.create(new_req)
        
        # Broadcast the new request for the live feed
        await self._broadcast_new_request(saved)
        return saved

    async def _merge_requests(self, existing: EnrichedRequest, new_data: dict) -> EnrichedRequest:
        # Update existing request with any missing metadata
        changed = False
        if not existing.application and new_data.get("application"):
            existing.application = new_data["application"]
            changed = True
        if not existing.project and new_data.get("project"):
            existing.project = new_data["project"]
            changed = True
        if not existing.user_id and new_data.get("user_id"):
            existing.user_id = new_data["user_id"]
            changed = True

        if changed:
            existing.is_reconciled = True
            await self.repo.session.commit()
            await self.repo.session.refresh(existing)

        return existing

    async def _broadcast_new_request(self, req: EnrichedRequest) -> None:
        data = {
            "request_id": req.request_id,
            "model": req.model,
            "total_tokens": req.total_tokens,
            "latency_ms": req.latency_ms,
            "application": req.application,
            "timestamp": req.timestamp.isoformat() if req.timestamp else None
        }
        await event_bus.publish("new_request", data)

    async def ingest_aggregate_usage(self, records: list[dict]) -> int:
        """Upsert provider-level aggregate usage (OpenAI / Anthropic admin polls).

        Each record describes one (provider, model, time bucket) with running
        token totals. Re-polling the same bucket updates the row in place, so
        partial hourly buckets fill in without double counting.
        """
        ingested = 0
        for rec in records:
            provider = rec.get("provider") or settings.default_provider
            bucket_start = _parse_timestamp(rec.get("bucket_start")) or datetime.now(
                timezone.utc
            )
            bucket_end = _parse_timestamp(rec.get("bucket_end"))
            model = rec.get("model") or "unknown"
            request_id = rec.get("request_id") or _aggregate_request_id(
                provider, model, bucket_start
            )

            meta = dict(rec.get("metadata") or {})
            if rec.get("num_requests") is not None:
                meta["num_requests"] = rec["num_requests"]
            if bucket_end is not None:
                meta["bucket_end"] = bucket_end.isoformat()

            row = EnrichedRequest(
                request_id=request_id,
                source=rec.get("source"),
                provider=provider,
                timestamp=bucket_start,
                model=model,
                prompt_tokens=int(rec.get("prompt_tokens") or 0),
                completion_tokens=int(rec.get("completion_tokens") or 0),
                total_tokens=int(rec.get("total_tokens") or 0),
                application=rec.get("application") or provider,
                req_metadata=meta,
                is_reconciled=True,
            )
            await self.repo.upsert(row)
            ingested += 1

        if ingested:
            logger.info("Ingested %d aggregate usage records", ingested)
            await event_bus.publish(
                "new_request",
                {"aggregate": True, "ingested": ingested},
            )
        return ingested
