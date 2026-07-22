from sqlalchemy.ext.asyncio import AsyncSession
from app.models.aggregation import Aggregation

class AggregationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, aggregation: Aggregation) -> Aggregation:
        self.session.add(aggregation)
        await self.session.commit()
        await self.session.refresh(aggregation)
        return aggregation
