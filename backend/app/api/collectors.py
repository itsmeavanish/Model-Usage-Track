from fastapi import APIRouter, Depends
from app.collectors.manager import CollectorManager
from app.dependencies import get_collector_manager

router = APIRouter()


@router.get("/status")
async def get_collectors_status(manager: CollectorManager = Depends(get_collector_manager)):
    return await manager.get_all_health()


@router.post("/{collector_type}/toggle")
async def toggle_collector(
    collector_type: str,
    enable: bool,
    manager: CollectorManager = Depends(get_collector_manager),
):
    collector = manager.get_collector(collector_type)
    if not collector:
        return {"error": "Collector not found"}

    if enable and not collector.is_running:
        await collector.start()
    elif not enable and collector.is_running:
        await collector.stop()

    return {"status": "success", "collector": collector_type, "is_running": collector.is_running}
