from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.enriched_request import EnrichedRequest

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

    async def upsert(self, row: EnrichedRequest) -> EnrichedRequest:
        """Insert, or update token counts + metadata if request_id already exists.

        Used by the provider aggregate collectors (OpenAI / Anthropic admin usage
        polls): each (provider, model, bucket) is re-queried as its bucket fills,
        so later polls must overwrite the running totals rather than be skipped.
        """
        existing = await self.get_by_id(row.request_id)
        if existing is None:
            self.session.add(row)
            await self.session.commit()
            await self.session.refresh(row)
            return row

        changed = False
        # Running totals / metadata are overwritten each poll as buckets fill.
        for attr in ("prompt_tokens", "completion_tokens", "total_tokens", "req_metadata"):
            value = getattr(row, attr, None)
            if value is None:
                continue
            if getattr(existing, attr) != value:
                setattr(existing, attr, value)
                changed = True
        # Keep the provider/model labels fresh in case a poll adds detail.
        for attr in ("provider", "model", "application"):
            value = getattr(row, attr, None)
            if value and getattr(existing, attr) != value:
                setattr(existing, attr, value)
                changed = True
        if changed:
            await self.session.commit()
            await self.session.refresh(existing)
        return existing
