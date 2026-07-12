from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.session import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSONB, default=dict)
    chunk_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    website = relationship("Website", back_populates="document_chunks")
