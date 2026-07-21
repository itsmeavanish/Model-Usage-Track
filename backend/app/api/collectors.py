from fastapi import APIRouter
from app.collectors.manager import CollectorManager

# In a real app, CollectorManager would be a singleton or injected
# We'll instantiate a placeholder here for the endpoints, but it should be
# the same instance used in lifespan.
manager = CollectorManager()

router = APIRouter()

@router.get("/status")
async def get_collectors_status():
    return await manager.get_all_health()

@router.post("/{collector_type}/toggle")
async def toggle_collector(collector_type: str, enable: bool):
    collector = manager.get_collector(collector_type)
    if not collector:
        return {"error": "Collector not found"}
        
    if enable and not collector.is_running:
        await collector.start()
    elif not enable and collector.is_running:
        await collector.stop()
        
    return {"status": "success", "collector": collector_type, "is_running": collector.is_running}
