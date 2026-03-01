from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import logging
import asyncio
import time


class CoinGeckoService:
    """
    CoinGecko API service for fetching cryptocurrency price data.
    
    Free tier limits:
    - 10-30 calls/minute
    - No API key required for basic endpoints
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    # Rate limiting: max 10 requests per minute to be safe
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_WINDOW = 60  # seconds
    
    # Common coin ID mappings (CoinGecko uses lowercase IDs)
    COIN_ALIASES = {
        "btc": "bitcoin",
        "eth": "ethereum",
        "sol": "solana",
        "xrp": "ripple",
        "ada": "cardano",
        "doge": "dogecoin",
        "dot": "polkadot",
        "matic": "matic-network",
        "polygon": "matic-network",
        "link": "chainlink",
        "avax": "avalanche-2",
        "uni": "uniswap",
        "atom": "cosmos",
        "ltc": "litecoin",
        "bnb": "binancecoin",
        "shib": "shiba-inu",
        "pepe": "pepe",
        "arb": "arbitrum",
        "op": "optimism",
        # Meme coins
        "wif": "dogwifcoin",
        "wifhat": "dogwifcoin",
        "dogwifhat": "dogwifcoin",
        "bonk": "bonk",
        "floki": "floki",
        "mog": "mog-coin",
        "popcat": "popcat",
        "brett": "brett",
        "neiro": "neiro-3",
        "goat": "goatseus-maximus",
        "pnut": "peanut-the-squirrel",
        "act": "act-i-the-ai-prophecy",
        "turbo": "turbo",
        "fartcoin": "fartcoin",
        # More major coins
        "sui": "sui",
        "apt": "aptos",
        "aptos": "aptos",
        "sei": "sei-network",
        "inj": "injective-protocol",
        "tia": "celestia",
        "jup": "jupiter-exchange-solana",
        "render": "render-token",
        "rndr": "render-token",
        "fet": "fetch-ai",
        "near": "near",
        "ton": "the-open-network",
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._client: Optional[httpx.AsyncClient] = None
        self._request_times: List[float] = []
        self._cache: Dict[str, tuple] = {}  # Simple cache: key -> (data, expiry_time)
        self._cache_ttl = 60  # Cache for 60 seconds
    
    async def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        # Remove old timestamps
        self._request_times = [t for t in self._request_times if now - t < self.RATE_LIMIT_WINDOW]
        
        if len(self._request_times) >= self.RATE_LIMIT_REQUESTS:
            # Wait until oldest request expires
            wait_time = self.RATE_LIMIT_WINDOW - (now - self._request_times[0]) + 0.5
            if wait_time > 0:
                self.logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        self._request_times.append(time.time())
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            data, expiry = self._cache[key]
            if time.time() < expiry:
                return data
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Set value in cache."""
        self._cache[key] = (data, time.time() + self._cache_ttl)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"Accept": "application/json"},
            )
        return self._client
    
    def _normalize_coin_id(self, coin: str) -> str:
        """Convert coin symbol/alias to CoinGecko ID."""
        coin_lower = coin.lower().strip()
        return self.COIN_ALIASES.get(coin_lower, coin_lower)
    
    async def get_current_price(
        self, 
        coins: List[str], 
        vs_currency: str = "usd",
        include_24h_change: bool = True,
        include_market_cap: bool = True,
    ) -> Dict[str, Any]:
        """
        Get current price for one or more coins.
        
        Args:
            coins: List of coin IDs or symbols (e.g., ["bitcoin", "eth", "sol"])
            vs_currency: Target currency (default: usd)
            include_24h_change: Include 24h price change percentage
            include_market_cap: Include market cap
        """
        # Normalize coin IDs
        coin_ids = [self._normalize_coin_id(c) for c in coins]
        cache_key = f"price:{','.join(sorted(coin_ids))}:{vs_currency}"
        
        # Check cache
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        # Rate limit
        await self._rate_limit()
        
        client = await self._get_client()
        
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": vs_currency,
            "include_24hr_change": str(include_24h_change).lower(),
            "include_market_cap": str(include_market_cap).lower(),
        }
        
        response = await client.get(f"{self.BASE_URL}/simple/price", params=params)
        response.raise_for_status()
        
        data = response.json()
        self._set_cache(cache_key, data)
        return data
    
    async def get_historical_price(
        self,
        coin: str,
        date: datetime,
        vs_currency: str = "usd",
    ) -> Dict[str, Any]:
        """
        Get historical price for a specific date.
        
        Args:
            coin: Coin ID or symbol
            date: Date to get price for
            vs_currency: Target currency
        """
        coin_id = self._normalize_coin_id(coin)
        date_str = date.strftime("%d-%m-%Y")
        cache_key = f"history:{coin_id}:{date_str}:{vs_currency}"
        
        # Check cache
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        # Rate limit
        await self._rate_limit()
        
        client = await self._get_client()
        
        params = {"date": date_str, "localization": "false"}
        
        response = await client.get(
            f"{self.BASE_URL}/coins/{coin_id}/history",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        
        market_data = data.get("market_data", {})
        
        result = {
            "coin": coin_id,
            "date": date.isoformat(),
            "price": market_data.get("current_price", {}).get(vs_currency),
            "market_cap": market_data.get("market_cap", {}).get(vs_currency),
            "volume": market_data.get("total_volume", {}).get(vs_currency),
        }
        
        self._set_cache(cache_key, result)
        return result
    
    async def get_price_range(
        self,
        coin: str,
        from_date: datetime,
        to_date: datetime,
        vs_currency: str = "usd",
    ) -> Dict[str, Any]:
        """
        Get historical prices for a date range.
        
        Args:
            coin: Coin ID or symbol
            from_date: Start date
            to_date: End date
            vs_currency: Target currency
            
        Returns:
            Dict with prices array [[timestamp, price], ...]
        """
        coin_id = self._normalize_coin_id(coin)
        
        # Convert to UNIX timestamps
        from_ts = int(from_date.timestamp())
        to_ts = int(to_date.timestamp())
        
        cache_key = f"range:{coin_id}:{from_ts}:{to_ts}:{vs_currency}"
        
        # Check cache (longer TTL for historical data)
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        # Rate limit
        await self._rate_limit()
        
        client = await self._get_client()
        
        params = {
            "vs_currency": vs_currency,
            "from": from_ts,
            "to": to_ts,
        }
        
        response = await client.get(
            f"{self.BASE_URL}/coins/{coin_id}/market_chart/range",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        
        # Convert timestamps to ISO format
        prices = []
        for ts, price in data.get("prices", []):
            dt = datetime.fromtimestamp(ts / 1000)  # CoinGecko uses milliseconds
            prices.append({
                "timestamp": dt.isoformat(),
                "price": price,
            })
        
        result = {
            "coin": coin_id,
            "vs_currency": vs_currency,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "prices": prices,
            "total_points": len(prices),
        }
        
        self._set_cache(cache_key, result)
        return result
    
    async def get_coin_info(self, coin: str) -> Dict[str, Any]:
        """
        Get detailed information about a coin.
        
        Args:
            coin: Coin ID or symbol
        """
        client = await self._get_client()
        coin_id = self._normalize_coin_id(coin)
        
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        }
        
        response = await client.get(
            f"{self.BASE_URL}/coins/{coin_id}",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        
        market_data = data.get("market_data", {})
        
        return {
            "id": data.get("id"),
            "symbol": data.get("symbol"),
            "name": data.get("name"),
            "image": data.get("image", {}).get("small"),
            "current_price": market_data.get("current_price", {}).get("usd"),
            "market_cap": market_data.get("market_cap", {}).get("usd"),
            "market_cap_rank": market_data.get("market_cap_rank"),
            "total_volume": market_data.get("total_volume", {}).get("usd"),
            "high_24h": market_data.get("high_24h", {}).get("usd"),
            "low_24h": market_data.get("low_24h", {}).get("usd"),
            "price_change_24h": market_data.get("price_change_24h"),
            "price_change_percentage_24h": market_data.get("price_change_percentage_24h"),
            "price_change_percentage_7d": market_data.get("price_change_percentage_7d"),
            "price_change_percentage_30d": market_data.get("price_change_percentage_30d"),
            "ath": market_data.get("ath", {}).get("usd"),
            "ath_date": market_data.get("ath_date", {}).get("usd"),
            "atl": market_data.get("atl", {}).get("usd"),
            "atl_date": market_data.get("atl_date", {}).get("usd"),
            "circulating_supply": market_data.get("circulating_supply"),
            "total_supply": market_data.get("total_supply"),
            "max_supply": market_data.get("max_supply"),
        }
    
    async def search_coins(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for coins by name or symbol.
        
        Args:
            query: Search query
        """
        client = await self._get_client()
        
        params = {"query": query}
        
        response = await client.get(f"{self.BASE_URL}/search", params=params)
        response.raise_for_status()
        data = response.json()
        
        coins = []
        for coin in data.get("coins", [])[:20]:  # Limit to 20 results
            coins.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol"),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "thumb": coin.get("thumb"),
            })
        
        return coins
    
    async def get_trending(self) -> List[Dict[str, Any]]:
        """Get trending coins (top 7 by search popularity) with price data."""
        client = await self._get_client()
        
        # Get trending coins
        response = await client.get(f"{self.BASE_URL}/search/trending")
        response.raise_for_status()
        data = response.json()
        
        trending = []
        coin_ids = []
        
        for item in data.get("coins", []):
            coin = item.get("item", {})
            coin_id = coin.get("id")
            if coin_id:
                coin_ids.append(coin_id)
                trending.append({
                    "id": coin_id,
                    "symbol": coin.get("symbol", "").upper(),
                    "name": coin.get("name"),
                    "market_cap_rank": coin.get("market_cap_rank"),
                    "thumb": coin.get("thumb"),
                    "price_change_percentage_24h": 0,  # Will be updated below
                    "current_price": 0,
                })
        
        # Fetch price data for trending coins (if we have any)
        if coin_ids and len(coin_ids) <= 10:
            try:
                await self._rate_limit()
                price_response = await client.get(
                    f"{self.BASE_URL}/simple/price",
                    params={
                        "ids": ",".join(coin_ids[:7]),  # Limit to 7 to save API calls
                        "vs_currencies": "usd",
                        "include_24hr_change": "true",
                    }
                )
                price_response.raise_for_status()
                price_data = price_response.json()
                
                # Update trending coins with price data
                for coin in trending:
                    coin_id = coin["id"]
                    if coin_id in price_data:
                        coin["current_price"] = price_data[coin_id].get("usd", 0)
                        coin["price_change_percentage_24h"] = round(
                            price_data[coin_id].get("usd_24h_change", 0), 2
                        )
            except Exception as e:
                self.logger.warning(f"Failed to fetch price data for trending coins: {e}")
        
        return trending
    
    async def get_fear_greed_index(self) -> Dict[str, Any]:
        """Get Bitcoin Fear & Greed Index from Alternative.me API."""
        client = await self._get_client()
        
        try:
            response = await client.get(
                "https://api.alternative.me/fng/",
                params={"limit": 1}
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("data") and len(data["data"]) > 0:
                fng = data["data"][0]
                return {
                    "value": int(fng.get("value", 50)),
                    "classification": fng.get("value_classification", "Neutral"),
                    "timestamp": fng.get("timestamp"),
                }
        except Exception as e:
            self.logger.warning(f"Failed to fetch Fear & Greed Index: {e}")
        
        # Return neutral if failed
        return {
            "value": 50,
            "classification": "Neutral",
            "timestamp": None,
        }
    
    async def get_top_coins_by_market_cap(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top coins by market cap with price data."""
        cache_key = f"top_coins:{limit}"
        
        # Check cache
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        await self._rate_limit()
        client = await self._get_client()
        
        response = await client.get(
            f"{self.BASE_URL}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            }
        )
        response.raise_for_status()
        data = response.json()
        
        coins = []
        for coin in data:
            coins.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "current_price": coin.get("current_price", 0),
                "price_change_percentage_24h": round(coin.get("price_change_percentage_24h", 0), 2),
                "market_cap_rank": coin.get("market_cap_rank"),
                "image": coin.get("image"),
            })
        
        self._set_cache(cache_key, coins)
        return coins

    async def get_memecoins(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top memecoins by market cap with price data."""
        cache_key = f"memecoins:{limit}"
        
        # Check cache
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        await self._rate_limit()
        client = await self._get_client()
        
        # CoinGecko meme category
        response = await client.get(
            f"{self.BASE_URL}/coins/markets",
            params={
                "vs_currency": "usd",
                "category": "meme-token",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            }
        )
        response.raise_for_status()
        data = response.json()
        
        coins = []
        for coin in data:
            coins.append({
                "id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "current_price": coin.get("current_price", 0),
                "price_change_percentage_24h": round(coin.get("price_change_percentage_24h", 0), 2),
                "market_cap_rank": coin.get("market_cap_rank"),
                "image": coin.get("image"),
            })
        
        self._set_cache(cache_key, coins)
        return coins


# Singleton instance
coingecko_service = CoinGeckoService()
