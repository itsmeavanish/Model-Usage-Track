import logging
from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

class LogCollector(BaseCollector):
    def __init__(self):
        super().__init__("log")
        self.is_healthy = True

    async def start(self) -> None:
        if not settings.log_collector_enabled:
            logger.info("LogCollector is disabled in settings.")
            return
            
        self.is_running = True
        logger.info(f"LogCollector started, watching {len(settings.log_watch_paths)} paths")

    async def stop(self) -> None:
        self.is_running = False
        logger.info("LogCollector stopped.")

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.is_healthy
        }
