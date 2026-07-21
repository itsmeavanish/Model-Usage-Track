from sqlalchemy import Column, Integer, String, Float, DateTime
from app.models.base import Base

class Aggregation(Base):
    __tablename__ = "aggregation"

    id = Column(Integer, primary_key=True, index=True)
    period = Column(String, index=True) # hourly, daily, weekly, monthly
    period_start = Column(DateTime(timezone=True), index=True)
    period_end = Column(DateTime(timezone=True))
    total_requests = Column(Integer, default=0)
    total_prompt_tokens = Column(Integer, default=0)
    total_completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0.0)
    p95_latency_ms = Column(Float, default=0.0)
    model = Column(String, nullable=True) # NULL for aggregate
    application = Column(String, nullable=True) # NULL for aggregate
    official_percentage = Column(Float, nullable=True) # From quota snapshot at period_end
