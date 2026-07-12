from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    users = relationship("User", back_populates="business", cascade="all, delete-orphan")
    websites = relationship("Website", back_populates="business", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="business", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="business", cascade="all, delete-orphan")
    plan = relationship("Plan", back_populates="businesses")
