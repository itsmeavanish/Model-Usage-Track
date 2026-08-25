from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta
import logging
from app.repositories.request_repository import RequestRepository
from app.repositories.quota_repository import QuotaRepository
from app.models.enriched_request import EnrichedRequest
from app.config import settings

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _period_start(period: str) -> datetime:
    now = _now()
    if period == "hourly":
        return now - timedelta(hours=24)
    if period == "weekly":
        return now - timedelta(days=7)
    if period == "monthly":
        return now - timedelta(days=30)
    # default daily -> last 7 days for summary
    return now - timedelta(days=7)


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.req_repo = RequestRepository(db)
        self.quota_repo = QuotaRepository(db)
        self.db = db

    async def get_summary(self, period: str = "daily", user_id: str | None = None) -> dict:
        since = _period_start(period)
        stmt = select(
            func.count(EnrichedRequest.id),
            func.coalesce(func.sum(EnrichedRequest.prompt_tokens), 0),
            func.coalesce(func.sum(EnrichedRequest.completion_tokens), 0),
            func.coalesce(func.sum(EnrichedRequest.total_tokens), 0),
            func.coalesce(func.avg(EnrichedRequest.latency_ms), 0.0),
        ).where(EnrichedRequest.timestamp >= since)

        if user_id:
            stmt = stmt.where(EnrichedRequest.user_id == user_id)

        row = (await self.db.execute(stmt)).one()
        return {
            "period": period,
            "since": since.isoformat(),
            "user_id": user_id,
            "total_requests": int(row[0] or 0),
            "total_prompt_tokens": int(row[1] or 0),
            "total_completion_tokens": int(row[2] or 0),
            "total_tokens": int(row[3] or 0),
            "avg_latency_ms": float(row[4] or 0.0),
        }

    async def get_trends(self, days: int = 7, user_id: str | None = None) -> list:
        since = _now() - timedelta(days=days)
        day_expr = func.date(EnrichedRequest.timestamp).label("day")
        stmt = (
            select(
                day_expr,
                func.coalesce(func.sum(EnrichedRequest.total_tokens), 0).label("tokens"),
                func.count(EnrichedRequest.id).label("requests"),
            )
            .where(EnrichedRequest.timestamp >= since)
            .group_by("day")
            .order_by("day")
        )
        if user_id:
            stmt = stmt.where(EnrichedRequest.user_id == user_id)

        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "date": row.day,  # already a 'YYYY-MM-DD' string from func.date()
                "tokens": int(row.tokens or 0),
                "requests": int(row.requests or 0),
            }
            for row in rows
        ]

    async def get_model_breakdown(self, user_id: str | None = None) -> list:
        stmt = (
            select(
                EnrichedRequest.model,
                func.coalesce(func.sum(EnrichedRequest.total_tokens), 0).label("tokens"),
                func.count(EnrichedRequest.id).label("requests"),
            )
            .group_by(EnrichedRequest.model)
            .order_by(func.sum(EnrichedRequest.total_tokens).desc())
        )
        if user_id:
            stmt = stmt.where(EnrichedRequest.user_id == user_id)

        rows = (await self.db.execute(stmt)).all()
        return [
            {"name": row.model or "unknown", "tokens": int(row.tokens or 0), "requests": int(row.requests or 0)}
            for row in rows
        ]

    async def get_application_breakdown(self, user_id: str | None = None) -> list:
        stmt = (
            select(
                EnrichedRequest.application,
                func.coalesce(func.sum(EnrichedRequest.total_tokens), 0).label("tokens"),
                func.count(EnrichedRequest.id).label("requests"),
            )
            .group_by(EnrichedRequest.application)
            .order_by(func.sum(EnrichedRequest.total_tokens).desc())
        )
        if user_id:
            stmt = stmt.where(EnrichedRequest.user_id == user_id)

        rows = (await self.db.execute(stmt)).all()
        return [
            {"name": row.application or "unknown", "tokens": int(row.tokens or 0), "requests": int(row.requests or 0)}
            for row in rows
        ]

    async def get_user_breakdown(self) -> list:
        stmt = (
            select(
                EnrichedRequest.user_id,
                func.coalesce(func.sum(EnrichedRequest.total_tokens), 0).label("tokens"),
                func.count(EnrichedRequest.id).label("requests"),
            )
            .where(EnrichedRequest.user_id.isnot(None))
            .group_by(EnrichedRequest.user_id)
            .order_by(func.sum(EnrichedRequest.total_tokens).desc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {"name": row.user_id or "unknown", "tokens": int(row.tokens or 0), "requests": int(row.requests or 0)}
            for row in rows
        ]

    async def get_provider_breakdown(self, period: str | None = None) -> list:
        """Usage split across model providers (zai / openai / anthropic).

        Rows with a NULL provider are legacy Z.ai rows captured before the
        provider column existed — they are bucketed as the default ("zai").
        """
        provider_expr = func.coalesce(
            EnrichedRequest.provider, settings.default_provider
        ).label("provider")
        stmt = (
            select(
                provider_expr,
                func.coalesce(func.sum(EnrichedRequest.total_tokens), 0).label("tokens"),
                func.count(EnrichedRequest.id).label("requests"),
            )
            # Group by the coalesced expression itself — grouping by the raw
            # column would split legacy NULL rows into a second "zai" bucket.
            .group_by(provider_expr)
            .order_by(func.sum(EnrichedRequest.total_tokens).desc())
        )
        if period:
            stmt = stmt.where(EnrichedRequest.timestamp >= _period_start(period))

        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "name": row.provider,
                "tokens": int(row.tokens or 0),
                "requests": int(row.requests or 0),
            }
            for row in rows
        ]

    async def get_my_usage(self) -> dict:
        identity = settings.user_identity
        if not identity:
            return {
                "configured": False,
                "user_id": None,
                "summary": await self.get_summary(),
                "trends": await self.get_trends(),
                "models": [],
            }
        return {
            "configured": True,
            "user_id": identity,
            "summary": await self.get_summary(user_id=identity),
            "trends": await self.get_trends(user_id=identity),
            "models": await self.get_model_breakdown(user_id=identity),
        }

    async def get_me_vs_total(self) -> dict:
        total_summary = await self.get_summary()
        total_trends_raw = await self.get_trends()

        identity = settings.user_identity
        my_summary = await self.get_summary(user_id=identity) if identity else {
            "total_requests": 0, "total_tokens": 0
        }
        my_trends_raw = await self.get_trends(user_id=identity) if identity else []

        my_by_date = {row["date"]: row["tokens"] for row in my_trends_raw}
        trends = [
            {
                "date": row["date"],
                "mine": my_by_date.get(row["date"], 0),
                "total": row["tokens"],
            }
            for row in total_trends_raw
        ]

        return {
            "identity": identity,
            "mine": {
                "requests": my_summary.get("total_requests", 0),
                "tokens": my_summary.get("total_tokens", 0),
            },
            "total": {
                "requests": total_summary.get("total_requests", 0),
                "tokens": total_summary.get("total_tokens", 0),
            },
            "trends": trends,
        }

    async def get_heatmap(self, days: int = 84) -> list:
        since = _now() - timedelta(days=days)
        day_expr = func.date(EnrichedRequest.timestamp).label("day")
        stmt = (
            select(
                day_expr,
                func.coalesce(func.sum(EnrichedRequest.total_tokens), 0).label("tokens"),
                func.count(EnrichedRequest.id).label("requests"),
            )
            .where(EnrichedRequest.timestamp >= since)
            .group_by("day")
            .order_by("day")
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "date": row.day,
                "tokens": int(row.tokens or 0),
                "requests": int(row.requests or 0),
            }
            for row in rows
        ]

    async def get_peak_hours(self, days: int = 7) -> dict:
        """Token usage bucketed by hour-of-day over the trailing window.

        Timestamps are stored in UTC, but an hour-of-day chart only makes sense
        in the viewer's local zone (the backend runs on the user's own machine),
        so UTC hour buckets from SQL are re-bucketed into local hours here.
        """
        since = _now() - timedelta(days=days)
        bucket_expr = func.strftime("%Y-%m-%dT%H", EnrichedRequest.timestamp).label("bucket")
        stmt = (
            select(
                bucket_expr,
                func.coalesce(func.sum(EnrichedRequest.total_tokens), 0).label("tokens"),
                func.count(EnrichedRequest.id).label("requests"),
            )
            .where(EnrichedRequest.timestamp >= since)
            .group_by("bucket")
            .order_by("bucket")
        )
        rows = (await self.db.execute(stmt)).all()

        tokens_by_hour = [0] * 24
        requests_by_hour = [0] * 24
        for row in rows:
            local_hour = (
                datetime.strptime(row.bucket, "%Y-%m-%dT%H")
                .replace(tzinfo=timezone.utc)
                .astimezone()
                .hour
            )
            tokens_by_hour[local_hour] += int(row.tokens or 0)
            requests_by_hour[local_hour] += int(row.requests or 0)

        total_tokens = sum(tokens_by_hour)
        peak = None
        if total_tokens > 0:
            peak_hour = max(range(24), key=lambda h: tokens_by_hour[h])
            peak = {
                "hour": peak_hour,
                "tokens": tokens_by_hour[peak_hour],
                "requests": requests_by_hour[peak_hour],
                "share": round(tokens_by_hour[peak_hour] / total_tokens * 100.0, 1),
            }

        return {
            "days": days,
            "timezone": datetime.now().astimezone().tzname(),
            "hours": [
                {"hour": h, "tokens": tokens_by_hour[h], "requests": requests_by_hour[h]}
                for h in range(24)
            ],
            "peak": peak,
            "total_tokens": total_tokens,
        }

    async def calculate_burn_rate(self, window_minutes: int = 60) -> dict:
        since = _now() - timedelta(minutes=window_minutes)
        stmt = select(func.coalesce(func.sum(EnrichedRequest.total_tokens), 0)).where(
            EnrichedRequest.timestamp >= since
        )
        tokens_last_window = int((await self.db.execute(stmt)).scalar_one() or 0)
        tokens_per_hour = int(tokens_last_window * (60.0 / max(window_minutes, 1)))

        # Estimate exhaustion using latest 5-hour quota snapshot, if any
        snapshot = await self.quota_repo.get_latest_snapshot()
        estimated_exhaustion = None
        window_label = None
        if snapshot and snapshot.limits:
            five_hour_limit = next((lim for lim in snapshot.limits if lim.unit == 3), snapshot.limits[0])
            pct = five_hour_limit.percentage or 0
            window_label = "5-hour" if five_hour_limit.unit == 3 else None
            if tokens_per_hour > 0 and pct < 100:
                hours_remaining = max(0.0, (100.0 - pct) / 100.0) * 5.0
                estimated_exhaustion = (_now() + timedelta(hours=hours_remaining)).isoformat()

        return {
            "tokens_per_hour": tokens_per_hour,
            "window_minutes": window_minutes,
            "window_label": window_label,
            "estimated_exhaustion": estimated_exhaustion,
        }

    async def calculate_unattributed_usage(self) -> dict:
        """
        Gap between official Z.ai quota percentage and the sum of tokens we have
        locally attributed via enrichment collectors (proxy/log/webhook).
        """
        snapshot = await self.quota_repo.get_latest_snapshot()
        if not snapshot or not snapshot.limits:
            return {
                "official_percentage": None,
                "enriched_percentage": 0.0,
                "unattributed_percentage": 0.0,
                "status": "No official quota data yet",
            }

        # Use the 5-hour window as the canonical "current consumption" view
        five_hour_limit = next((lim for lim in snapshot.limits if lim.unit == 3), snapshot.limits[0])
        official_pct = float(five_hour_limit.percentage or 0)

        # Count locally-tracked tokens within the same window
        window_hours = 5 if five_hour_limit.unit == 3 else 24
        since = _now() - timedelta(hours=window_hours)
        stmt = select(func.coalesce(func.sum(EnrichedRequest.total_tokens), 0)).where(
            EnrichedRequest.timestamp >= since
        )
        enriched_tokens = int((await self.db.execute(stmt)).scalar_one() or 0)

        # Heuristic: 200k tokens ~= 100% of a 5-hour window for default tier.
        # This constant should come from quota metadata in a fuller impl.
        window_capacity = 200_000
        enriched_pct = min(100.0, (enriched_tokens / window_capacity) * 100.0) if window_capacity else 0.0

        gap = max(0.0, official_pct - enriched_pct)
        status = "Healthy" if gap < 5 else ("Warning" if gap < 20 else "Critical")

        return {
            "official_percentage": official_pct,
            "enriched_percentage": enriched_pct,
            "unattributed_percentage": gap,
            "enriched_tokens": enriched_tokens,
            "status": status,
        }
