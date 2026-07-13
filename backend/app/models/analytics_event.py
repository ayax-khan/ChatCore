from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy import JSON
from app.db.session import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    properties = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
