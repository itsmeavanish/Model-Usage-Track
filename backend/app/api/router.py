from fastapi import APIRouter
from app.api import health, quota, websocket

api_router = APIRouter()

api_router.include_router(health.router, tags=["system"])
api_router.include_router(quota.router, prefix="/quota", tags=["quota"])
api_router.include_router(websocket.router, tags=["websocket"])
