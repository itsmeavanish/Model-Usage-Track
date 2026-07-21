from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.models.base import Base

class CollectorHealth(Base):
    __tablename__ = "collector_health"

    id = Column(Integer, primary_key=True, index=True)
    collector_type = Column(String, unique=True, index=True) # official, proxy, log, webhook
    last_success = Column(DateTime(timezone=True), nullable=True)
    last_failure = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(String, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    is_healthy = Column(Boolean, default=True)
