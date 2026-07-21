from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.models.enriched_request import EnrichedRequest
from typing import Sequence
from datetime import datetime

class RequestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, request: EnrichedRequest) -> EnrichedRequest:
        self.session.add(request)
        await self.session.commit()
        await self.session.refresh(request)
        return request

    async def get_by_id(self, request_id: str) -> EnrichedRequest | None:
        stmt = select(EnrichedRequest).where(EnrichedRequest.request_id == request_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
