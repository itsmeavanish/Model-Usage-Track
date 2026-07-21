from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.dependencies import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.reconciliation_service import ReconciliationService
from app.config import settings

router = APIRouter()

class WebhookPayload(BaseModel):
    request_id: Optional[str] = None
    source: str = "webhook"
    timestamp: Optional[str] = None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    status_code: int = 200
    application: Optional[str] = None
    project: Optional[str] = None
    machine: Optional[str] = None
    metadata: Dict[str, Any] = {}
    is_streaming: bool = False

def verify_webhook_secret(x_webhook_secret: Optional[str] = Header(None)):
    if settings.webhook_secret:
        if x_webhook_secret != settings.webhook_secret.get_secret_value():
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

@router.post("/ingest")
async def ingest_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_webhook_secret)
):
    if not settings.webhook_enabled:
        raise HTTPException(status_code=403, detail="Webhook collector is disabled")
        
    service = ReconciliationService(db)
    
    # Convert model to dict for ingestion
    request_data = payload.model_dump()
    
    # We parse the timestamp string to datetime in the service if needed,
    # or rely on SQLAlchemy's type coercion
    try:
        saved = await service.ingest_request(request_data)
        return {"status": "success", "request_id": saved.request_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
