from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    url = Column(String(2048), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="pending")
    crawl_interval_hours = Column(Integer, default=24)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    business = relationship("Business", back_populates="websites")
    document_chunks = relationship("DocumentChunk", back_populates="website", cascade="all, delete-orphan")
