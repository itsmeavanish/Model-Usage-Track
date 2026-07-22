from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey
from datetime import datetime, timezone
from app.models.base import Base

class EnrichedRequest(Base):
    __tablename__ = "enriched_request"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True, nullable=False)
    source = Column(String) # proxy, log, webhook
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    model = Column(String, index=True)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    status_code = Column(Integer, default=200)
    application = Column(String, index=True)
    project = Column(String)
    machine = Column(String)
    user_id = Column(String, index=True)
    req_metadata = Column(JSON, default=dict)
    is_streaming = Column(Boolean, default=False)
    
    is_reconciled = Column(Boolean, default=False, index=True)
    reconciled_with = Column(String, ForeignKey("enriched_request.request_id"), nullable=True)
