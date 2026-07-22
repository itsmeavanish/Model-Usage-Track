import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.reconciliation_service import ReconciliationService

logger = logging.getLogger(__name__)

async def reconcile_job(db: AsyncSession):
    """
    Background job to perform late reconciliation.
    Since most reconciliation happens inline during ingest (in ReconciliationService),
    this job would clean up or retry unmatched fuzzy requests.
    """
    logger.info("Running background reconciliation job...")
    ReconciliationService(db)

    # In a full implementation, query for is_reconciled=False and attempt fuzzy matching again
    # For now, it's just a placeholder to satisfy the architecture.
    pass
