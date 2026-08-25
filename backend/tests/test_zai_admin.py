"""Tests for the Z.ai admin (model-usage) collector and aggregate ingestion."""
from datetime import datetime, timedelta, timezone

from app.collectors.zai_admin import (
    _format_window,
    _normalize_response as zai_normalize,
)
from app.services.analytics_service import AnalyticsService
from app.services.reconciliation_service import ReconciliationService


def test_zai_normalize_builds_per_model_hourly_records():
    payload = {
        "x_time": ["2026-08-21 17:00", "2026-08-21 18:00"],
        "modelDataList": [
            {
                "modelName": "GLM-5.3",
                "sortOrder": 1,
                "tokensUsage": [3144161, 0],  # zero bucket must be skipped
                "modelCallCount": [12, 0],
            },
            {
                "modelName": "GLM-4.6V",
                "sortOrder": 2,
                "tokensUsage": [4204, 999],
            },
        ],
        "granularity": "hourly",
    }
    records = zai_normalize(payload)
    assert len(records) == 3  # 1 + 2, zero bucket dropped

    r = records[0]
    assert r["provider"] == "zai"
    assert r["source"] == "zai_admin"
    assert r["model"] == "glm-5.3"  # lowercased to match proxy-captured rows
    assert r["total_tokens"] == 3144161
    assert r["num_requests"] == 12
    assert r["bucket_start"] == datetime(2026, 8, 21, 17, 0, tzinfo=timezone.utc)
    assert r["bucket_end"] == datetime(2026, 8, 21, 18, 0, tzinfo=timezone.utc)

    # No per-bucket split is published; only the combined figure.
    assert r["prompt_tokens"] == 0 and r["completion_tokens"] == 0
    # modelCallCount missing entirely -> num_requests None, tokens still counted
    assert records[1]["num_requests"] is None
    assert records[1]["total_tokens"] == 4204


def test_zai_normalize_skips_unparseable_labels():
    payload = {
        "x_time": ["not-a-date", "2026-08-21 18:00"],
        "modelDataList": [{"modelName": "GLM-5.3", "tokensUsage": [10, 20]}],
    }
    records = zai_normalize(payload)
    assert len(records) == 1
    assert records[0]["total_tokens"] == 20


def test_zai_window_formatting_is_utc_naive():
    # 2026-08-21 23:00 IST == 17:30 UTC; the API wants naive UTC strings.
    ist = datetime(2026, 8, 21, 23, 0, tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)
    assert _format_window(ist) == "2026-08-21 17:30:00"


async def test_zai_admin_upsert_feeds_analytics(session):
    svc = ReconciliationService(session)
    record = {
        "provider": "zai",
        "source": "zai_admin",
        "model": "glm-5.3",
        "bucket_start": datetime(2026, 8, 21, 17, 0, tzinfo=timezone.utc),
        "bucket_end": datetime(2026, 8, 21, 18, 0, tzinfo=timezone.utc),
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 3144161,
        "num_requests": 12,
        "metadata": {"bucket": "zai_admin"},
    }
    await svc.ingest_aggregate_usage([record])

    # Re-poll the same bucket with a higher running total (bucket filling in).
    updated = {**record, "total_tokens": 4206899, "num_requests": 15}
    await svc.ingest_aggregate_usage([updated])

    a = AnalyticsService(session)
    models = {m["name"]: m for m in await a.get_model_breakdown()}
    assert models["glm-5.3"]["tokens"] == 4206899  # latest total wins
    assert models["glm-5.3"]["requests"] == 1  # not double-counted

    providers = {p["name"]: p["tokens"] for p in await a.get_provider_breakdown()}
    assert providers.get("zai") == 4206899
