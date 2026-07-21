from fastapi import APIRouter, Depends
from app.dependencies import get_db, get_official_collector
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.quota_service import QuotaService
from app.collectors.official import OfficialCollector

router = APIRouter()

def get_quota_service(db: AsyncSession = Depends(get_db), collector: OfficialCollector = Depends(get_official_collector)) -> QuotaService:
    return QuotaService(db, collector)

@router.get("/current")
async def get_current_quota(service: QuotaService = Depends(get_quota_service)):
    quota = await service.get_current_quota()
    if not quota:
        return {"error": "No quota data available yet"}
    return quota
