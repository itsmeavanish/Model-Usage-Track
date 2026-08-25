from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/summary")
async def get_summary(
    period: str = Query("daily", pattern="^(hourly|daily|weekly|monthly)$"),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_summary(period)


@router.get("/trends")
async def get_trends(
    days: int = Query(7, ge=1, le=365),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_trends(days)


@router.get("/by-model")
async def get_by_model(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_model_breakdown()


@router.get("/by-application")
async def get_by_application(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_application_breakdown()


@router.get("/by-user")
async def get_by_user(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_user_breakdown()


@router.get("/by-provider")
async def get_by_provider(
    period: str | None = Query(None, pattern="^(hourly|daily|weekly|monthly)$"),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_provider_breakdown(period)


@router.get("/me")
async def get_my_usage(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_my_usage()


@router.get("/me-vs-total")
async def get_me_vs_total(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.get_me_vs_total()


@router.get("/heatmap")
async def get_heatmap(
    days: int = Query(84, ge=1, le=365),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_heatmap(days)


@router.get("/peak-hours")
async def get_peak_hours(
    days: int = Query(7, ge=1, le=90),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_peak_hours(days)


@router.get("/burn-rate")
async def get_burn_rate(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.calculate_burn_rate()


@router.get("/unattributed")
async def get_unattributed(service: AnalyticsService = Depends(get_analytics_service)):
    return await service.calculate_unattributed_usage()
