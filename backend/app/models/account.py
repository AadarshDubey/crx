from sqlalchemy import String, DateTime, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

from app.database.connection import Base


class TrackedAccount(Base):
    """Model for Twitter/X accounts to track."""
    
    __tablename__ = "tracked_accounts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    handle: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Categorization
    category: Mapped[str] = mapped_column(String(50), default="general")  # influencer, analyst, project, news, whale
    priority: Mapped[int] = mapped_column(Integer, default=1)  # Higher = more important
    
    # Tracking config
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scrape_replies: Mapped[bool] = mapped_column(Boolean, default=False)
    scrape_retweets: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Stats
    followers_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tweets_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Scraping metadata
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_tweet_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scrape_errors: Mapped[int] = mapped_column(Integer, default=0)
    
    # Custom settings
    custom_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TrackedAccount(handle=@{self.handle}, category={self.category})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "handle": self.handle,
            "name": self.name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "category": self.category,
            "priority": self.priority,
            "is_active": self.is_active,
            "followers_count": self.followers_count,
            "last_scraped_at": self.last_scraped_at.isoformat() if self.last_scraped_at else None,
        }


# Predefined categories for accounts
ACCOUNT_CATEGORIES = [
    "influencer",   # Crypto influencers and personalities
    "analyst",      # Technical/fundamental analysts
    "project",      # Official project accounts (Bitcoin, Ethereum, etc.)
    "news",         # News outlet accounts
    "whale",        # Known whale/large holder accounts
    "developer",    # Core developers
    "exchange",     # Exchange official accounts
    "vc",          # Venture capital firms
    "general",      # General/uncategorized
]
