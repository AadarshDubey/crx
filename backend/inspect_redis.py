import asyncio
import redis.asyncio as redis
from app.config import settings
import json

async def main():
    print(f"Connecting to Redis at {settings.REDIS_URL}...")
    try:
        r = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await r.ping()
        print("✅ Connected to Redis")
        
        print("\n--- Redis Keys ---")
        cursor = 0
        total_keys = 0
        while True:
            cursor, keys = await r.scan(cursor)
            for key in keys:
                total_keys += 1
                ttl = await r.ttl(key)
                type_ = await r.type(key)
                
                print(f"Key: {key}")
                print(f"  Type: {type_}")
                print(f"  TTL:  {ttl}s")
                
                if type_ == 'string':
                    val = await r.get(key)
                    try:
                        parsed = json.loads(val)
                        print(f"  Value (JSON): {str(parsed)[:100]}...") 
                    except:
                        print(f"  Value: {val[:100]}...")
                elif type_ == 'list':
                    length = await r.llen(key)
                    print(f"  Length: {length}")
                elif type_ == 'set':
                    length = await r.scard(key)
                    print(f"  Size: {length}")
                elif type_ == 'hash':
                    length = await r.hlen(key)
                    print(f"  Fields: {length}")
                
                print("-" * 20)
                
            if cursor == 0:
                break
                
        print(f"\nTotal Keys Found: {total_keys}")
        
        await r.aclose()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
