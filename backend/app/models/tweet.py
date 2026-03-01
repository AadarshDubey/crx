from sqlalchemy import String, Text, DateTime, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

from app.database.connection import Base


class Tweet(Base):
    """Model for storing scraped tweets."""
    
    __tablename__ = "tweets"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_handle: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    author_name: Mapped[str] = mapped_column(String(100), nullable=True)
    author_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Engagement metrics
    likes: Mapped[int] = mapped_column(default=0)
    retweets: Mapped[int] = mapped_column(default=0)
    replies: Mapped[int] = mapped_column(default=0)
    views: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Timestamps
    tweet_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # AI Analysis
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # positive, negative, neutral
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    topics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of detected topics/coins
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Vector embedding reference
    embedding_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Original tweet URL
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Is this a retweet/quote?
    is_retweet: Mapped[bool] = mapped_column(default=False)
    is_reply: Mapped[bool] = mapped_column(default=False)
    
    def __repr__(self):
        return f"<Tweet(id={self.id}, author=@{self.author_handle})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "content": self.content,
            "author": {
                "handle": self.author_handle,
                "name": self.author_name,
                "avatar": self.author_avatar,
            },
            "engagement": {
                "likes": self.likes,
                "retweets": self.retweets,
                "replies": self.replies,
                "views": self.views,
            },
            "created_at": self.tweet_created_at.isoformat() + "Z",
            "scraped_at": self.scraped_at.isoformat() + "Z",
            "sentiment": {
                "label": self.sentiment_label,
                "score": self.sentiment_score,
            } if self.sentiment_label else None,
            "topics": self.topics or [],
            "url": self.url,
            "is_retweet": self.is_retweet,
            "is_reply": self.is_reply,
        }
