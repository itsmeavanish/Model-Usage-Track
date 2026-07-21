from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()

def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)

@router.get("/summary")
async def get_summary(period: str = "daily", service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_summary(period)

@router.get("/trends")
async def get_trends(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_trends()

@router.get("/by-model")
async def get_by_model(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_model_breakdown()

@router.get("/by-application")
async def get_by_application(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_application_breakdown()

@router.get("/burn-rate")
async def get_burn_rate(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.calculate_burn_rate()

@router.get("/unattributed")
async def get_unattributed(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.calculate_unattributed_usage()
