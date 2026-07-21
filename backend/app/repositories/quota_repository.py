from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.quota_snapshot import QuotaSnapshot, QuotaLimit

class QuotaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_snapshot(self, snapshot: QuotaSnapshot) -> QuotaSnapshot:
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_latest_snapshot(self) -> QuotaSnapshot | None:
        stmt = select(QuotaSnapshot).order_by(QuotaSnapshot.polled_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
