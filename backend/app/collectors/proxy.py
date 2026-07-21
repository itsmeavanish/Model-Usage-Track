import logging
from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

class ProxyCollector(BaseCollector):
    def __init__(self):
        super().__init__("proxy")
        self.is_healthy = True

    async def start(self) -> None:
        if not settings.proxy_enabled:
            logger.info("ProxyCollector is disabled in settings.")
            return
            
        self.is_running = True
        # In a real implementation, we would start an HTTP proxy server here
        # (e.g., using aiohttp server or intercepting via middleware in FastAPI)
        # For Milestone 3, we mock the background start
        logger.info(f"ProxyCollector started on port {settings.proxy_port}, targeting {settings.proxy_target_url}")

    async def stop(self) -> None:
        self.is_running = False
        logger.info("ProxyCollector stopped.")

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.is_healthy
        }
