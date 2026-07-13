from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from app.db.session import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    features = Column(JSON, default=dict)
    monthly_fee = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    businesses = relationship("Business", back_populates="plan")
