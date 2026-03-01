from sqlalchemy import String, Text, DateTime, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

from app.database.connection import Base


class NewsArticle(Base):
    """Model for storing scraped news articles."""
    
    __tablename__ = "news_articles"
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Source information
    source_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    # Author
    author: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Timestamps
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Categorization
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # market, regulation, defi, etc.
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # AI Analysis
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_points: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    mentioned_coins: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Vector embedding reference
    embedding_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Processing status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    def __repr__(self):
        return f"<NewsArticle(id={self.id}, source={self.source_id})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "excerpt": self.excerpt,
            "source": {
                "id": self.source_id,
                "name": self.source_name,
            },
            "url": self.url,
            "image_url": self.image_url,
            "author": self.author,
            "published_at": self.published_at.isoformat() + "Z",
            "scraped_at": self.scraped_at.isoformat() + "Z",
            "category": self.category,
            "tags": self.tags or [],
            "sentiment": {
                "label": self.sentiment_label,
                "score": self.sentiment_score,
            } if self.sentiment_label else None,
            "summary": self.summary,
            "key_points": self.key_points or [],
            "mentioned_coins": self.mentioned_coins or [],
        }


class NewsSource(Base):
    """Model for news sources to track."""
    
    __tablename__ = "news_sources"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    rss_feed: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Scraping config
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scrape_frequency_minutes: Mapped[int] = mapped_column(default=30)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Source metadata
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.8)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<NewsSource(id={self.id}, name={self.name})>"
