"""Scheduler job: poll a provider admin usage API and upsert aggregates.

The provider collectors (OpenAI / Anthropic) expose ``fetch_usage(start, end)``
returning normalized per-(model, bucket) records. This job picks a trailing
window, fetches, and hands the records to ReconciliationService for idempotent
upsert. Usage data from both platforms lags a few minutes, so we always re-query
the last few hours and let the upsert settle partial hourly buckets.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)

# Look-back window. Covers ~2 hourly buckets; the most recent is still filling,
# so each poll refreshes it until the hour rolls over.
_POLL_LOOKBACK_HOURS = 3


async def poll_provider_usage_job(collector, provider_name: str) -> None:
    if not getattr(collector, "is_running", False):
        return

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=_POLL_LOOKBACK_HOURS)
    logger.info("Polling %s usage [%s .. %s]", provider_name, start, end)

    try:
        records = await collector.fetch_usage(start, end)
    except Exception:
        # fetch_usage already recorded health + logged the error.
        return

    if not records:
        logger.info("No %s usage records returned.", provider_name)
        return

    # Deferred import avoids a circular dependency with app.dependencies.
    from app.dependencies import async_session_maker

    async with async_session_maker() as session:
        service = ReconciliationService(session)
        await service.ingest_aggregate_usage(records)
