"""
Shared fixtures for all backend tests.
Everything is mocked — no real DB, Redis, or API keys needed.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# ============ Database Fixtures ============

@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


# ============ Model Fixtures ============

@pytest.fixture
def sample_tweet():
    """Create a sample Tweet model instance."""
    from app.models.tweet import Tweet

    tweet = Tweet(
        id="abc123def456",
        content="Bitcoin is looking very bullish today! $BTC to the moon 🚀",
        author_handle="CryptoGuru",
        author_name="Crypto Guru",
        author_avatar="https://example.com/avatar.jpg",
        likes=1500,
        retweets=320,
        replies=45,
        views=50000,
        tweet_created_at=datetime(2026, 3, 20, 12, 0, 0),
        scraped_at=datetime(2026, 3, 20, 12, 5, 0),
        sentiment_label="positive",
        sentiment_score=0.85,
        topics=["bitcoin", "market"],
        summary="Bullish outlook on Bitcoin",
        embedding_id="emb_abc123",
        url="https://x.com/CryptoGuru/status/123",
        is_retweet=False,
        is_reply=False,
    )
    return tweet


@pytest.fixture
def sample_tweet_no_sentiment():
    """Create a Tweet with no sentiment analysis."""
    from app.models.tweet import Tweet

    return Tweet(
        id="no_sentiment_001",
        content="Just a random tweet",
        author_handle="TestUser",
        author_name="Test User",
        tweet_created_at=datetime(2026, 3, 20, 10, 0, 0),
        scraped_at=datetime(2026, 3, 20, 10, 1, 0),
        sentiment_label=None,
        sentiment_score=None,
        is_retweet=False,
        is_reply=False,
    )


@pytest.fixture
def sample_account():
    """Create a sample TrackedAccount model instance."""
    from app.models.account import TrackedAccount

    return TrackedAccount(
        id=1,
        handle="VitalikButerin",
        name="Vitalik Buterin",
        bio="Ethereum co-founder",
        avatar_url="https://example.com/vitalik.jpg",
        category="founder",
        priority=5,
        is_active=True,
        scrape_replies=False,
        scrape_retweets=False,
        followers_count=5000000,
        tweets_count=12000,
        last_scraped_at=datetime(2026, 3, 20, 11, 0, 0),
        scrape_errors=0,
        created_at=datetime(2026, 1, 1, 0, 0, 0),
        updated_at=datetime(2026, 3, 20, 11, 0, 0),
    )


@pytest.fixture
def sample_account_never_scraped():
    """Create a TrackedAccount that has never been scraped."""
    from app.models.account import TrackedAccount

    return TrackedAccount(
        id=2,
        handle="NewAccount",
        name=None,
        category="general",
        priority=1,
        is_active=True,
        last_scraped_at=None,
        created_at=datetime(2026, 3, 20, 0, 0, 0),
        updated_at=datetime(2026, 3, 20, 0, 0, 0),
    )


@pytest.fixture
def sample_news_article():
    """Create a sample NewsArticle model instance."""
    from app.models.news import NewsArticle

    return NewsArticle(
        id="news_abc123",
        title="Bitcoin Hits New All-Time High",
        content="Bitcoin surged past $100,000 today in a historic milestone...",
        excerpt="BTC breaks $100K barrier",
        source_id="coindesk",
        source_name="CoinDesk",
        url="https://coindesk.com/article/btc-ath",
        image_url="https://coindesk.com/images/btc.jpg",
        author="Jane Doe",
        published_at=datetime(2026, 3, 20, 8, 0, 0),
        scraped_at=datetime(2026, 3, 20, 8, 5, 0),
        category="market",
        tags=["bitcoin", "ath"],
        sentiment_label="positive",
        sentiment_score=0.92,
        summary="Bitcoin reached a new ATH above $100K",
        key_points=["BTC > $100K", "Record trading volume"],
        mentioned_coins=["BTC"],
        is_processed=True,
    )


# ============ Redis Cache Fixtures ============

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.ping = AsyncMock()
    redis_mock.scan = AsyncMock(return_value=(0, []))
    redis_mock.info = AsyncMock(return_value={"used_memory_human": "1.5M"})
    redis_mock.close = AsyncMock()
    return redis_mock
