from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings
from app.api.router import api_router
from app.dependencies import (
    engine,
    collector_manager,
    official_collector,
    openai_collector,
    anthropic_collector,
    async_session_maker,
)
from app.jobs.scheduler import start_scheduler, stop_scheduler, add_job
from app.jobs.quota_poll import poll_quota_job
from app.jobs.provider_poll import poll_provider_usage_job
from app.services.quota_service import QuotaService
from app.core.migrations import run_dev_migrations
import app.models  # noqa: F401 - ensure models are registered on Base.metadata

logger = logging.getLogger(__name__)


async def _quota_poll_task() -> None:
    async with async_session_maker() as session:
        service = QuotaService(session, official_collector)
        await poll_quota_job(service)


async def _openai_poll_task() -> None:
    await poll_provider_usage_job(openai_collector, "openai")


async def _anthropic_poll_task() -> None:
    await poll_provider_usage_job(anthropic_collector, "anthropic")


@asynccontextmanager
async def lifespan(app: FastAPI):
    data_dir = Path(settings.database_url.replace("sqlite+aiosqlite:///", "").split("?")[0]).parent
    data_dir.mkdir(parents=True, exist_ok=True)

    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured.")

    # Additive migrations for existing dev databases (e.g. new provider column).
    await run_dev_migrations(engine)

    await collector_manager.start_all()

    add_job(_quota_poll_task, settings.poll_interval_seconds, "quota_poll")

    # Provider admin-usage pollers are only scheduled when enabled + configured.
    if settings.openai_enabled:
        add_job(
            _openai_poll_task,
            settings.openai_poll_interval_seconds,
            "openai_usage_poll",
        )
    if settings.anthropic_enabled:
        add_job(
            _anthropic_poll_task,
            settings.anthropic_poll_interval_seconds,
            "anthropic_usage_poll",
        )

    start_scheduler()

    app.state.collector_manager = collector_manager
    yield

    stop_scheduler()
    await collector_manager.stop_all()
    await engine.dispose()


app = FastAPI(
    title="GLM Usage Monitor",
    description="Z.ai Account-Wide GLM-5.2 Usage Monitoring Service",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
