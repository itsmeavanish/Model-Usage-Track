"""Tests for the OpenAI / Anthropic provider collectors and aggregate ingestion."""
from datetime import datetime, timedelta, timezone

from app.collectors.openai import _normalize_bucket as openai_normalize
from app.collectors.anthropic import _normalize_bucket as anthropic_normalize
from app.services.analytics_service import AnalyticsService
from app.services.reconciliation_service import ReconciliationService


def test_openai_normalize_flattens_results():
    bucket = {
        "start_time": 1721620800.0,  # 2024-07-22T04:00:00Z
        "end_time": 1721624400.0,
        "results": [
            {"model": "gpt-4o", "input_tokens": 1200, "output_tokens": 300,
             "num_model_requests": 4, "input_cached_tokens": 100},
            {"model": "gpt-4o-mini", "input_tokens": 0, "output_tokens": 0},
        ],
    }
    records = openai_normalize(bucket)
    assert len(records) == 1  # zero-token model dropped
    r = records[0]
    assert r["provider"] == "openai"
    assert r["source"] == "openai_admin"
    assert r["model"] == "gpt-4o"
    assert r["prompt_tokens"] == 1200
    assert r["completion_tokens"] == 300
    assert r["total_tokens"] == 1500
    assert r["num_requests"] == 4
    assert r["bucket_start"] == datetime(2024, 7, 22, 4, 0, tzinfo=timezone.utc)


def test_anthropic_normalize_sums_cache_tokens():
    bucket = {
        "starting_at": "2025-01-15T10:00:00Z",
        "ending_at": "2025-01-15T11:00:00Z",
        "results": [
            {
                "model": "claude-sonnet-4-5",
                "uncached_input_tokens": 500,
                "cache_read_input_tokens": 200,
                "output_tokens": 150,
                "cache_creation": {
                    "ephemeral_5m_input_tokens": 100,
                    "ephemeral_1h_input_tokens": 50,
                },
            }
        ],
    }
    records = anthropic_normalize(bucket)
    assert len(records) == 1
    r = records[0]
    # input = uncached + cache_read + cache_creation(100+50)
    assert r["prompt_tokens"] == 500 + 200 + 150
    assert r["completion_tokens"] == 150
    assert r["total_tokens"] == 1000
    assert r["provider"] == "anthropic"
    assert r["num_requests"] is None


async def test_aggregate_upsert_is_idempotent_and_updates(session):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    svc = ReconciliationService(session)
    record = {
        "provider": "openai",
        "source": "openai_admin",
        "model": "gpt-4o",
        "bucket_start": now,
        "bucket_end": now + timedelta(hours=1),
        "prompt_tokens": 1200,
        "completion_tokens": 300,
        "total_tokens": 1500,
        "num_requests": 4,
        "metadata": {"bucket": "openai_admin"},
    }

    await svc.ingest_aggregate_usage([record])

    # Re-poll the same bucket with higher running totals (bucket filling in).
    updated = {**record, "prompt_tokens": 1800, "completion_tokens": 450,
               "total_tokens": 2250, "num_requests": 7}
    await svc.ingest_aggregate_usage([updated])

    a = AnalyticsService(session)
    summary = await a.get_summary()
    assert summary["total_requests"] == 1  # not double-counted
    assert summary["total_tokens"] == 2250  # latest totals win

    providers = {p["name"]: p["tokens"] for p in await a.get_provider_breakdown()}
    assert providers.get("openai") == 2250


async def test_provider_breakdown_buckets_legacy_rows_as_default(session):
    svc = ReconciliationService(session)
    # A request with no provider behaves like a legacy GLM row (NULL provider).
    await svc.ingest_request({
        "request_id": "legacy-1",
        "source": "webhook",
        "model": "glm-5.2",
        "total_tokens": 999,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    a = AnalyticsService(session)
    providers = {p["name"]: p["tokens"] for p in await a.get_provider_breakdown()}
    assert providers.get("zai") == 999
