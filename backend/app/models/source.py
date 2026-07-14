from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.session import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    snippet = Column(Text, nullable=False)
    offset = Column(Integer, default=0)
    url = Column(Text, nullable=True)
    score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunk = relationship("DocumentChunk")
    message = relationship("Message", back_populates="sources")
