from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base

class QuotaSnapshot(Base):
    __tablename__ = "quota_snapshot"

    id = Column(Integer, primary_key=True, index=True)
    polled_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    level = Column(String)
    raw_response = Column(JSON)

    limits = relationship("QuotaLimit", back_populates="snapshot", cascade="all, delete-orphan")

class QuotaLimit(Base):
    __tablename__ = "quota_limit"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("quota_snapshot.id"))
    limit_type = Column(String) # TOKENS_LIMIT | TIME_LIMIT
    unit = Column(Integer) # 3=5hr, 6=weekly, 5=monthly
    percentage = Column(Float)
    next_reset_time = Column(DateTime(timezone=True))

    snapshot = relationship("QuotaSnapshot", back_populates="limits")
