"""Unit tests for ReconciliationService and AnalyticsService against an in-memory DB."""
import pytest
from datetime import datetime, timezone, timedelta

from app.services.reconciliation_service import ReconciliationService
from app.services.analytics_service import AnalyticsService
from app.models.quota_snapshot import QuotaSnapshot, QuotaLimit
from app.repositories.quota_repository import QuotaRepository


async def _seed_request(db, **overrides):
    svc = ReconciliationService(db)
    payload = {
        "request_id": overrides.get("request_id", f"req-{overrides.get('user_id','x')}-{overrides.get('tokens',0)}-{overrides.get('ts')}"),
        "source": "webhook",
        "model": overrides.get("model", "glm-5.2"),
        "prompt_tokens": overrides.get("prompt_tokens", 100),
        "completion_tokens": overrides.get("completion_tokens", 50),
        "total_tokens": overrides.get("tokens", overrides.get("prompt_tokens", 100) + overrides.get("completion_tokens", 50)),
        "application": overrides.get("application", "opencode"),
        "user_id": overrides.get("user_id"),
        "timestamp": overrides.get("ts", datetime.now(timezone.utc)).isoformat(),
    }
    return await svc.ingest_request(payload)


@pytest.mark.asyncio
async def test_reconciliation_dedupes_by_request_id(session):
    await _seed_request(session, request_id="dup-1", tokens=200, user_id="alice")
    await _seed_request(session, request_id="dup-1", tokens=200, user_id="alice")
    a = AnalyticsService(session)
    summary = await a.get_summary()
    assert summary["total_requests"] == 1
    assert summary["total_tokens"] == 200


@pytest.mark.asyncio
async def test_reconciliation_merges_metadata(session):
    await _seed_request(session, request_id="m-1", tokens=200, user_id=None)
    svc = ReconciliationService(session)
    await svc.ingest_request({
        "request_id": "m-1",
        "model": "glm-5.2",
        "total_tokens": 200,
        "user_id": "bob",
    })
    a = AnalyticsService(session)
    by_user = await a.get_user_breakdown()
    assert any(u["name"] == "bob" for u in by_user)


@pytest.mark.asyncio
async def test_summary_filters_by_user(session):
    await _seed_request(session, request_id="u1", tokens=100, user_id="alice")
    await _seed_request(session, request_id="u2", tokens=400, user_id="bob")
    a = AnalyticsService(session)
    alice = await a.get_summary(user_id="alice")
    total = await a.get_summary()
    assert alice["total_tokens"] == 100
    assert total["total_tokens"] == 500


@pytest.mark.asyncio
async def test_trends_groups_by_day(session):
    now = datetime.now(timezone.utc)
    await _seed_request(session, request_id="t1", tokens=100, user_id="a", ts=now)
    await _seed_request(session, request_id="t2", tokens=300, user_id="a", ts=now - timedelta(days=1))
    a = AnalyticsService(session)
    trends = await a.get_trends(days=7)
    assert len(trends) == 2
    assert sum(t["tokens"] for t in trends) == 400


@pytest.mark.asyncio
async def test_model_and_application_breakdowns(session):
    await _seed_request(session, request_id="b1", tokens=100, user_id="a", model="glm-5.2", application="opencode")
    await _seed_request(session, request_id="b2", tokens=300, user_id="a", model="glm-4-plus", application="vscode")
    a = AnalyticsService(session)
    models = {m["name"]: m["tokens"] for m in await a.get_model_breakdown()}
    apps = {m["name"]: m["tokens"] for m in await a.get_application_breakdown()}
    assert models == {"glm-5.2": 100, "glm-4-plus": 300}
    assert apps == {"opencode": 100, "vscode": 300}


@pytest.mark.asyncio
async def test_burn_rate(session):
    await _seed_request(session, request_id="br1", tokens=2000, user_id="a")
    a = AnalyticsService(session)
    br = await a.calculate_burn_rate(window_minutes=60)
    assert br["tokens_per_hour"] == 2000


@pytest.mark.asyncio
async def test_peak_hours_buckets_by_local_hour(session):
    now = datetime.now(timezone.utc)
    heavy_ts = now.replace(hour=10, minute=5, second=0, microsecond=0)
    light_ts = now.replace(hour=4, minute=5, second=0, microsecond=0)
    await _seed_request(session, request_id="ph1", tokens=300, user_id="a", ts=heavy_ts)
    await _seed_request(session, request_id="ph2", tokens=100, user_id="a", ts=light_ts)

    a = AnalyticsService(session)
    result = await a.get_peak_hours(days=7)

    assert len(result["hours"]) == 24
    assert result["total_tokens"] == 400
    # Buckets are re-labeled in the server's local zone, so compute the
    # expected hour with the same conversion the service performs.
    assert result["peak"]["hour"] == heavy_ts.astimezone().hour
    assert result["peak"]["tokens"] == 300
    assert result["peak"]["share"] == 75.0


@pytest.mark.asyncio
async def test_peak_hours_empty_when_no_usage(session):
    a = AnalyticsService(session)
    result = await a.get_peak_hours(days=7)
    assert result["peak"] is None
    assert result["total_tokens"] == 0
    assert all(h["tokens"] == 0 for h in result["hours"])


@pytest.mark.asyncio
async def test_unattributed_uses_latest_snapshot(session):
    snap = QuotaSnapshot(level="default", raw_response={})
    snap.limits.append(QuotaLimit(limit_type="TOKENS_LIMIT", unit=3, percentage=80.0))
    await QuotaRepository(session).create_snapshot(snap)

    await _seed_request(session, request_id="un1", tokens=1000, user_id="a")

    a = AnalyticsService(session)
    res = await a.calculate_unattributed_usage()
    assert res["official_percentage"] == 80.0
    assert res["status"] == "Critical"  # tiny enriched %, big gap
