"""
Unit tests for app/services/cache.py
Redis operations tested with mocked client.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch

from app.services.cache import RedisCache


@pytest.fixture
def cache_instance():
    """Create a fresh RedisCache instance (disconnected)."""
    return RedisCache()


@pytest.fixture
def connected_cache(mock_redis):
    """Create a RedisCache with a mocked connected Redis client."""
    cache = RedisCache()
    cache._redis = mock_redis
    cache._available = True
    return cache


# ============ Unavailable Cache (Graceful Degradation) ============

class TestUnavailableCache:
    @pytest.mark.asyncio
    async def test_get_returns_none_when_unavailable(self, cache_instance):
        result = await cache_instance.get("any_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_silently_noop_when_unavailable(self, cache_instance):
        # Should not raise
        await cache_instance.set("key", {"data": "value"})

    @pytest.mark.asyncio
    async def test_invalidate_noop_when_unavailable(self, cache_instance):
        await cache_instance.invalidate("pattern:*")

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self, cache_instance):
        result = await cache_instance.health_check()
        assert result["status"] == "disconnected"


# ============ Connected Cache Operations ============

class TestConnectedCache:
    @pytest.mark.asyncio
    async def test_get_cache_miss(self, connected_cache):
        connected_cache._redis.get = AsyncMock(return_value=None)
        result = await connected_cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, connected_cache):
        cached_data = {"tweets": [1, 2, 3], "total": 3}
        connected_cache._redis.get = AsyncMock(
            return_value=json.dumps(cached_data)
        )
        result = await connected_cache.get("tweets:all")
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_set_stores_json(self, connected_cache):
        data = {"key": "value"}
        await connected_cache.set("test_key", data, ttl=60)
        connected_cache._redis.set.assert_called_once()
        call_args = connected_cache._redis.set.call_args
        assert call_args[0][0] == "test_key"
        assert json.loads(call_args[0][1]) == data
        assert call_args[1]["ex"] == 60

    @pytest.mark.asyncio
    async def test_health_check_connected(self, connected_cache):
        result = await connected_cache.health_check()
        assert result["status"] == "connected"
        assert "used_memory" in result

    @pytest.mark.asyncio
    async def test_get_handles_redis_error(self, connected_cache):
        connected_cache._redis.get = AsyncMock(
            side_effect=Exception("Connection lost")
        )
        result = await connected_cache.get("any_key")
        assert result is None  # Graceful fallback

    @pytest.mark.asyncio
    async def test_set_handles_redis_error(self, connected_cache):
        connected_cache._redis.set = AsyncMock(
            side_effect=Exception("Connection lost")
        )
        # Should not raise
        await connected_cache.set("key", "value")


# ============ Connection Lifecycle ============

class TestConnectionLifecycle:
    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self, connected_cache):
        await connected_cache.disconnect()
        connected_cache._redis.close.assert_called_once()
        assert connected_cache._available is False

    def test_is_available_property(self, cache_instance, connected_cache):
        assert cache_instance.is_available is False
        assert connected_cache.is_available is True
