from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.quota_repository import QuotaRepository
from app.collectors.official import OfficialCollector
from app.core.events import event_bus
from app.models.quota_snapshot import QuotaSnapshot

class QuotaService:
    def __init__(self, db: AsyncSession, collector: OfficialCollector):
        self.repo = QuotaRepository(db)
        self.collector = collector

    async def poll_and_store(self) -> QuotaSnapshot | None:
        try:
            snapshot = await self.collector.fetch_quota()
            saved_snapshot = await self.repo.create_snapshot(snapshot)
            await self._broadcast_update(saved_snapshot)
            return saved_snapshot
        except Exception as e:
            # We already logged in collector, just return None or raise
            return None

    async def get_current_quota(self) -> dict | None:
        snapshot = await self.repo.get_latest_snapshot()
        if not snapshot:
            return None
        return self._format_snapshot(snapshot)

    def _format_snapshot(self, snapshot: QuotaSnapshot) -> dict:
        limits = []
        for limit in snapshot.limits:
            window_label = "unknown"
            if limit.unit == 3: window_label = "5-hour"
            elif limit.unit == 6: window_label = "weekly"
            elif limit.unit == 5: window_label = "monthly"

            limits.append({
                "type": limit.limit_type,
                "unit": limit.unit,
                "percentage": limit.percentage,
                "next_reset_time": limit.next_reset_time.isoformat() if limit.next_reset_time else None,
                "window_label": window_label
            })

        return {
            "level": snapshot.level,
            "polled_at": snapshot.polled_at.isoformat() if snapshot.polled_at else None,
            "limits": limits
        }

    async def _broadcast_update(self, snapshot: QuotaSnapshot) -> None:
        data = self._format_snapshot(snapshot)
        await event_bus.publish("quota_update", data)
