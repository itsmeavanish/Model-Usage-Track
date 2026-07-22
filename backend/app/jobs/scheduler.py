from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")

def add_job(func, seconds: int, job_id: str):
    scheduler.add_job(
        func,
        trigger=IntervalTrigger(seconds=seconds),
        id=job_id,
        replace_existing=True
    )
    logger.info(f"Added job: {job_id} every {seconds}s")
