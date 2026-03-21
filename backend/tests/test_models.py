"""
Unit tests for model to_dict() serialization.
Tests Tweet, TrackedAccount, and NewsArticle models.
"""

import pytest
from datetime import datetime


# ============ Tweet Model ============

class TestTweetModel:
    def test_to_dict_structure(self, sample_tweet):
        d = sample_tweet.to_dict()
        assert d["id"] == "abc123def456"
        assert d["content"].startswith("Bitcoin")

        # Nested author
        assert d["author"]["handle"] == "CryptoGuru"
        assert d["author"]["name"] == "Crypto Guru"
        assert d["author"]["avatar"] == "https://example.com/avatar.jpg"

        # Nested engagement
        assert d["engagement"]["likes"] == 1500
        assert d["engagement"]["retweets"] == 320
        assert d["engagement"]["replies"] == 45
        assert d["engagement"]["views"] == 50000

        # Timestamps are ISO format with Z suffix
        assert d["created_at"].endswith("Z")
        assert d["scraped_at"].endswith("Z")

        # Sentiment
        assert d["sentiment"]["label"] == "positive"
        assert d["sentiment"]["score"] == 0.85

        # Other fields
        assert d["url"] == "https://x.com/CryptoGuru/status/123"
        assert d["is_retweet"] is False
        assert d["is_reply"] is False
        assert d["topics"] == ["bitcoin", "market"]

    def test_to_dict_no_sentiment(self, sample_tweet_no_sentiment):
        d = sample_tweet_no_sentiment.to_dict()
        assert d["sentiment"] is None

    def test_to_dict_empty_topics(self, sample_tweet_no_sentiment):
        d = sample_tweet_no_sentiment.to_dict()
        assert d["topics"] == []

    def test_repr(self, sample_tweet):
        r = repr(sample_tweet)
        assert "abc123def456" in r
        assert "CryptoGuru" in r


# ============ TrackedAccount Model ============

class TestTrackedAccountModel:
    def test_to_dict_structure(self, sample_account):
        d = sample_account.to_dict()
        assert d["id"] == 1
        assert d["handle"] == "VitalikButerin"
        assert d["name"] == "Vitalik Buterin"
        assert d["bio"] == "Ethereum co-founder"
        assert d["category"] == "founder"
        assert d["priority"] == 5
        assert d["is_active"] is True
        assert d["followers_count"] == 5000000

    def test_to_dict_with_last_scraped(self, sample_account):
        d = sample_account.to_dict()
        assert d["last_scraped_at"] is not None
        # Should be ISO format
        datetime.fromisoformat(d["last_scraped_at"])  # Should not raise

    def test_to_dict_never_scraped(self, sample_account_never_scraped):
        d = sample_account_never_scraped.to_dict()
        assert d["last_scraped_at"] is None
        assert d["name"] is None

    def test_repr(self, sample_account):
        r = repr(sample_account)
        assert "VitalikButerin" in r


# ============ NewsArticle Model ============

class TestNewsArticleModel:
    def test_to_dict_structure(self, sample_news_article):
        d = sample_news_article.to_dict()
        assert d["id"] == "news_abc123"
        assert d["title"] == "Bitcoin Hits New All-Time High"
        assert d["content"].startswith("Bitcoin surged")
        assert d["excerpt"] == "BTC breaks $100K barrier"

        # Nested source
        assert d["source"]["id"] == "coindesk"
        assert d["source"]["name"] == "CoinDesk"

        assert d["url"] == "https://coindesk.com/article/btc-ath"
        assert d["author"] == "Jane Doe"

        # Timestamps
        assert d["published_at"].endswith("Z")
        assert d["scraped_at"].endswith("Z")

        # AI analysis
        assert d["sentiment"]["label"] == "positive"
        assert d["sentiment"]["score"] == 0.92
        assert d["summary"] == "Bitcoin reached a new ATH above $100K"
        assert len(d["key_points"]) == 2
        assert d["mentioned_coins"] == ["BTC"]

    def test_to_dict_no_sentiment(self, sample_news_article):
        # Manually clear sentiment for this test
        sample_news_article.sentiment_label = None
        sample_news_article.sentiment_score = None
        d = sample_news_article.to_dict()
        assert d["sentiment"] is None

    def test_to_dict_empty_optional_lists(self, sample_news_article):
        sample_news_article.tags = None
        sample_news_article.key_points = None
        sample_news_article.mentioned_coins = None
        d = sample_news_article.to_dict()
        assert d["tags"] == []
        assert d["key_points"] == []
        assert d["mentioned_coins"] == []

    def test_repr(self, sample_news_article):
        r = repr(sample_news_article)
        assert "news_abc123" in r
        assert "coindesk" in r
