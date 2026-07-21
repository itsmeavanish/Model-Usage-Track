import logging
from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

class WebhookCollector(BaseCollector):
    def __init__(self):
        super().__init__("webhook")
        self.is_healthy = True

    async def start(self) -> None:
        if not settings.webhook_enabled:
            logger.info("WebhookCollector is disabled in settings.")
            return
            
        self.is_running = True
        logger.info("WebhookCollector started (ready to receive POSTs)")

    async def stop(self) -> None:
        self.is_running = False
        logger.info("WebhookCollector stopped.")

    async def get_health(self) -> dict:
        return {
            "name": self.name,
            "is_running": self.is_running,
            "is_healthy": self.is_healthy
        }
