from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from app.db.session import Base


class WebsitePage(Base):
    __tablename__ = "website_pages"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    url = Column(String(2048), nullable=False)
    title = Column(String(512), nullable=True)
    content_hash = Column(String(64), nullable=False)
    last_crawled_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    website = relationship("Website", backref="pages")
