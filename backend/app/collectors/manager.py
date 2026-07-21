import logging
from typing import Dict
from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

class CollectorManager:
    def __init__(self):
        self._collectors: Dict[str, BaseCollector] = {}

    def register(self, collector: BaseCollector) -> None:
        if collector.name in self._collectors:
            logger.warning(f"Collector {collector.name} already registered. Overwriting.")
        self._collectors[collector.name] = collector
        logger.info(f"Registered collector: {collector.name}")

    async def start_all(self) -> None:
        logger.info("Starting all registered collectors...")
        for name, collector in self._collectors.items():
            try:
                await collector.start()
                logger.info(f"Started collector: {name}")
            except Exception as e:
                logger.error(f"Failed to start collector {name}: {e}")

    async def stop_all(self) -> None:
        logger.info("Stopping all collectors...")
        for name, collector in self._collectors.items():
            try:
                await collector.stop()
                logger.info(f"Stopped collector: {name}")
            except Exception as e:
                logger.error(f"Failed to stop collector {name}: {e}")

    def get_collector(self, name: str) -> BaseCollector | None:
        return self._collectors.get(name)

    async def get_all_health(self) -> dict:
        return {name: await collector.get_health() for name, collector in self._collectors.items()}
