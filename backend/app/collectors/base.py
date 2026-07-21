from abc import ABC, abstractmethod
import asyncio
import logging

logger = logging.getLogger(__name__)

class BaseCollector(ABC):
    def __init__(self, name: str):
        self.name = name
        self.is_running = False
        self._task: asyncio.Task | None = None

    @abstractmethod
    async def start(self) -> None:
        """Start the collector's background process."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the collector's background process."""
        pass

    @abstractmethod
    async def get_health(self) -> dict:
        """Return health status of this collector."""
        pass
