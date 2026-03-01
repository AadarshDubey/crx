from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta

from app.services.prices.coingecko import coingecko_service
from app.services.cache import cache

router = APIRouter()

# Cache TTLs
PRICES_CACHE_TTL = 60       # 60 seconds for price data
FEAR_GREED_CACHE_TTL = 300  # 5 minutes for fear & greed


@router.get("/")
async def get_current_prices(
    coins: str = Query(..., description="Comma-separated list of coin IDs or symbols (e.g., 'btc,eth,sol')"),
    vs_currency: str = Query("usd", description="Target currency (usd, eur, btc, etc.)"),
):
    """
    Get current prices for one or more coins.
    
    Example: /api/prices/?coins=btc,eth,sol
    """
    try:
        coin_list = [c.strip() for c in coins.split(",")]
        data = await coingecko_service.get_current_price(
            coins=coin_list,
            vs_currency=vs_currency,
            include_24h_change=True,
            include_market_cap=True,
        )
        return {
            "prices": data,
            "vs_currency": vs_currency,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_price_history(
    coin: str = Query(..., description="Coin ID or symbol (e.g., 'btc', 'ethereum')"),
    from_date: Optional[datetime] = Query(None, description="Start date (ISO format). Defaults to 30 days ago."),
    to_date: Optional[datetime] = Query(None, description="End date (ISO format). Defaults to now."),
    vs_currency: str = Query("usd", description="Target currency"),
):
    """
    Get historical prices for a coin within a date range.
    
    Example: /api/prices/history?coin=btc&from_date=2025-12-01&to_date=2026-01-01
    """
    try:
        # Default date range: last 30 days
        if to_date is None:
            to_date = datetime.utcnow()
        if from_date is None:
            from_date = to_date - timedelta(days=30)
        
        data = await coingecko_service.get_price_range(
            coin=coin,
            from_date=from_date,
            to_date=to_date,
            vs_currency=vs_currency,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date")
async def get_price_on_date(
    coin: str = Query(..., description="Coin ID or symbol"),
    date: datetime = Query(..., description="Date to get price for (ISO format)"),
    vs_currency: str = Query("usd", description="Target currency"),
):
    """
    Get price for a specific date.
    
    Example: /api/prices/date?coin=btc&date=2025-12-25
    """
    try:
        data = await coingecko_service.get_historical_price(
            coin=coin,
            date=date,
            vs_currency=vs_currency,
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{coin}")
async def get_coin_info(coin: str):
    """
    Get detailed information about a coin.
    
    Example: /api/prices/info/bitcoin
    """
    try:
        data = await coingecko_service.get_coin_info(coin)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_coins(
    q: str = Query(..., description="Search query (coin name or symbol)"),
):
    """
    Search for coins by name or symbol.
    
    Example: /api/prices/search?q=bitcoin
    """
    try:
        coins = await coingecko_service.search_coins(q)
        return {
            "query": q,
            "results": coins,
            "total": len(coins),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending")
async def get_trending_coins():
    """
    Get trending coins (top 7 by search popularity on CoinGecko) with price data.
    """
    cached = await cache.get("prices:trending")
    if cached:
        return cached
    try:
        trending = await coingecko_service.get_trending()
        response = {
            "trending": trending,
            "total": len(trending),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await cache.set("prices:trending", response, ttl=PRICES_CACHE_TTL)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top")
async def get_top_coins(
    limit: int = Query(10, ge=1, le=50, description="Number of top coins to return"),
):
    """
    Get top coins by market cap with price data.
    """
    cache_key = f"prices:top:{limit}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    try:
        coins = await coingecko_service.get_top_coins_by_market_cap(limit)
        response = {
            "coins": coins,
            "total": len(coins),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await cache.set(cache_key, response, ttl=PRICES_CACHE_TTL)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memecoins")
async def get_memecoins(
    limit: int = Query(10, ge=1, le=50, description="Number of memecoins to return"),
):
    """
    Get top memecoins by market cap with price data.
    """
    cache_key = f"prices:memecoins:{limit}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    try:
        coins = await coingecko_service.get_memecoins(limit)
        response = {
            "coins": coins,
            "total": len(coins),
            "timestamp": datetime.utcnow().isoformat(),
        }
        await cache.set(cache_key, response, ttl=PRICES_CACHE_TTL)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fear-greed")
async def get_fear_greed_index():
    """
    Get Bitcoin Fear & Greed Index.
    
    Returns a value from 0-100:
    - 0-25: Extreme Fear
    - 25-45: Fear
    - 45-55: Neutral
    - 55-75: Greed
    - 75-100: Extreme Greed
    """
    cached = await cache.get("prices:fear_greed")
    if cached:
        return cached
    try:
        data = await coingecko_service.get_fear_greed_index()
        response = {
            "fear_greed": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await cache.set("prices:fear_greed", response, ttl=FEAR_GREED_CACHE_TTL)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
