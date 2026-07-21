import logging
from app.services.quota_service import QuotaService
from app.config import settings

logger = logging.getLogger(__name__)

async def poll_quota_job(quota_service: QuotaService):
    logger.info("Polling Z.ai for quota updates...")
    result = await quota_service.poll_and_store()
    if result:
        logger.info(f"Successfully polled quota. Next reset: {result.limits[0].next_reset_time if result.limits else 'N/A'}")
    else:
        logger.warning("Failed to poll or store quota updates.")
