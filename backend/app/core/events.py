import json
from typing import Callable, Awaitable, List

class EventBus:
    def __init__(self):
        self._subscribers: List[Callable[[str], Awaitable[None]]] = []

    def subscribe(self, callback: Callable[[str], Awaitable[None]]):
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str], Awaitable[None]]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def publish(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data})
        for sub in self._subscribers:
            try:
                await sub(message)
            except Exception:
                pass # Ignore failed subscribers

event_bus = EventBus()
