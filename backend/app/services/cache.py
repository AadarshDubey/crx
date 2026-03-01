"""
Redis cache service for API response caching.

Provides async Redis operations with graceful fallback when Redis is unavailable.
"""

import json
import logging
from typing import Optional, Any
from functools import wraps

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Async Redis cache with graceful degradation."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._available = False

    async def connect(self):
        """Initialize Redis connection."""
        try:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            await self._redis.ping()
            self._available = True
            logger.info(f"✅ Redis connected at {settings.REDIS_URL}")
        except Exception as e:
            self._available = False
            logger.warning(f"⚠️ Redis unavailable ({e}). Running without cache.")

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._available = False
            logger.info("Redis disconnected")

    @property
    def is_available(self) -> bool:
        return self._available

    async def get(self, key: str) -> Optional[Any]:
        """Get a cached value. Returns None on miss or error."""
        if not self._available:
            return None
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis GET error for '{key}': {e}")
        return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set a cached value with TTL in seconds."""
        if not self._available:
            return
        try:
            await self._redis.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception as e:
            logger.warning(f"Redis SET error for '{key}': {e}")

    async def invalidate(self, pattern: str):
        """Delete all keys matching a pattern (e.g., 'news:*')."""
        if not self._available:
            return
        try:
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._redis.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"Cache invalidated: {pattern}")
        except Exception as e:
            logger.warning(f"Redis invalidation error for '{pattern}': {e}")

    async def health_check(self) -> dict:
        """Check Redis health status."""
        if not self._available:
            return {"status": "disconnected", "error": "Redis not available"}
        try:
            await self._redis.ping()
            info = await self._redis.info("memory")
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Singleton instance
cache = RedisCache()
