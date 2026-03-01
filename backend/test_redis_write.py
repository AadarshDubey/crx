import asyncio
import redis.asyncio as redis
from app.config import settings
from app.services.cache import cache

async def test_cache():
    print(f"Testing Redis connection to: {settings.REDIS_URL}")
    
    # 1. Test direct connection
    try:
        r = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await r.ping()
        print("✅ Direct Redis connection successful")
        await r.aclose()
    except Exception as e:
        print(f"❌ Direct Redis connection failed: {e}")
        return

    # 2. Test Cache Service
    print("\nTesting Cache Service...")
    await cache.connect()
    
    if not cache._available:
        print("❌ Cache service reports unavailable")
        return

    # Write
    await cache.set("test_key", {"status": "ok"}, ttl=60)
    print("✅ Written 'test_key' to cache")

    # Read
    val = await cache.get("test_key")
    if val and val.get("status") == "ok":
        print(f"✅ Read 'test_key' from cache: {val}")
    else:
        print(f"❌ Failed to read 'test_key'. Got: {val}")

    await cache.disconnect()

if __name__ == "__main__":
    asyncio.run(test_cache())
