from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.quota_snapshot import QuotaSnapshot

class QuotaRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_snapshot(self, snapshot: QuotaSnapshot) -> QuotaSnapshot:
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        # Eagerly load limits so callers don't trigger a sync lazy-load.
        stmt = (
            select(QuotaSnapshot)
            .options(selectinload(QuotaSnapshot.limits))
            .where(QuotaSnapshot.id == snapshot.id)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def get_latest_snapshot(self) -> QuotaSnapshot | None:
        stmt = (
            select(QuotaSnapshot)
            .options(selectinload(QuotaSnapshot.limits))
            .order_by(QuotaSnapshot.polled_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
