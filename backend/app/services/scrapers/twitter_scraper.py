from typing import List, Optional
from datetime import datetime, timedelta
import httpx
from bs4 import BeautifulSoup
import asyncio
import re
import random
import hashlib

from app.services.scrapers.base_scraper import BaseScraper, ScrapedItem
from app.config import settings


class TwitterScraper(BaseScraper):
    """
    Twitter/X scraper using RapidAPI Twitter endpoints.
    
    Priority:
    1. RapidAPI Twitter API (twitter-api45) - if RAPIDAPI_KEY configured
    2. Official Twitter API v2 (if TWITTER_BEARER_TOKEN configured)
    3. Fallback error
    """
    
    # RapidAPI Twitter endpoint (twitter-api45 - working as of Jan 2026)
    RAPIDAPI_HOST = "twitter-api45.p.rapidapi.com"
    RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_HOST}"
    
    def __init__(self):
        super().__init__("twitter")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client
    
    async def scrape(
        self, 
        target: str, 
        max_tweets: int = 50,
        include_replies: bool = False,
        include_retweets: bool = False,
        since_id: Optional[str] = None,
    ) -> List[ScrapedItem]:
        """
        Scrape tweets from a Twitter account.
        
        Args:
            target: Twitter handle (without @)
            max_tweets: Maximum number of tweets to fetch
            include_replies: Whether to include reply tweets
            include_retweets: Whether to include retweets
            since_id: Only fetch tweets newer than this ID
        """
        target = target.lstrip("@")
        
        # Try RapidAPI first if configured
        if settings.RAPIDAPI_KEY:
            try:
                return await self._scrape_via_rapidapi(target, max_tweets, include_replies, include_retweets)
            except Exception as e:
                self.logger.warning(f"RapidAPI scraping failed: {e}")
                # Try official API as fallback
                if settings.TWITTER_BEARER_TOKEN:
                    try:
                        return await self._scrape_via_api(target, max_tweets, since_id)
                    except Exception as e2:
                        self.logger.warning(f"Official API also failed: {e2}")
                raise Exception(f"All Twitter scraping methods failed: {e}")
        
        # Try official API if configured
        if settings.TWITTER_BEARER_TOKEN:
            return await self._scrape_via_api(target, max_tweets, since_id)
        
        raise Exception("No Twitter API credentials configured. Please set RAPIDAPI_KEY or TWITTER_BEARER_TOKEN")
    
    async def _scrape_via_rapidapi(
        self, 
        handle: str, 
        max_tweets: int,
        include_replies: bool = False,
        include_retweets: bool = False,
    ) -> List[ScrapedItem]:
        """Scrape using RapidAPI twitter-api45 endpoint."""
        client = await self._get_client()
        
        headers = {
            "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
            "X-RapidAPI-Host": self.RAPIDAPI_HOST,
            "Cache-Control": "no-cache",
        }
        
        # Get user timeline with cache-busting timestamp
        timeline_url = f"{self.RAPIDAPI_BASE_URL}/timeline.php"
        import time
        params = {
            "screenname": handle,
            "_": str(int(time.time() * 1000)),  # Cache buster
        }
        
        self.logger.info(f"Fetching timeline for @{handle} (timestamp: {params['_']})")
        response = await client.get(timeline_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        self.logger.info(f"RapidAPI response status: {data.get('status')}, timeline items: {len(data.get('timeline', []))}")
        
        if data.get("status") != "ok":
            raise Exception(f"API returned error status: {data.get('status')}")
        
        # Extract user info
        user_info = data.get("user", {})
        author_name = user_info.get("name", handle)
        author_avatar = user_info.get("avatar", "")
        
        # Parse tweets from timeline
        items = []
        timeline = data.get("timeline", [])
        
        for tweet in timeline:
            try:
                tweet_id = str(tweet.get("tweet_id", ""))
                tweet_text = tweet.get("text", "")
                
                if not tweet_id or not tweet_text:
                    continue
                
                # Check if it's a retweet or reply
                is_retweet = tweet_text.startswith("RT @")
                is_reply = str(tweet.get("conversation_id")) != str(tweet.get("tweet_id"))
                
                # Filter based on settings
                if not include_retweets and is_retweet:
                    continue
                if not include_replies and is_reply:
                    continue
                
                # Parse created_at
                created_at_str = tweet.get("created_at", "")
                try:
                    # Twitter format: "Thu Jan 01 14:41:56 +0000 2026"
                    created_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
                    created_at = created_at.replace(tzinfo=None)
                except:
                    created_at = datetime.utcnow()
                
                # Get engagement metrics
                likes = tweet.get("favorites", 0)
                retweets_count = tweet.get("retweets", 0)
                replies_count = tweet.get("replies", 0)
                views = tweet.get("views", 0)
                if isinstance(views, str):
                    views = int(views) if views.isdigit() else 0
                
                item = ScrapedItem(
                    id=tweet_id,
                    content=tweet_text,
                    source=f"twitter:@{handle}",
                    url=f"https://twitter.com/{handle}/status/{tweet_id}",
                    created_at=created_at,
                    scraped_at=datetime.utcnow(),
                    metadata={
                        "author_handle": handle,
                        "author_name": author_name,
                        "author_avatar": author_avatar,
                        "likes": likes,
                        "retweets": retweets_count,
                        "replies": replies_count,
                        "views": views,
                        "is_retweet": is_retweet,
                        "is_reply": is_reply,
                        "lang": tweet.get("lang", ""),
                        "method": "rapidapi",
                    },
                )
                items.append(item)
                
                if len(items) >= max_tweets:
                    break
                    
            except Exception as e:
                self.logger.debug(f"Failed to parse tweet: {e}")
                continue
        
        # Sort by created_at descending (newest first)
        items.sort(key=lambda x: x.created_at, reverse=True)
        
        if items:
            self.logger.info(f"Latest tweet from @{handle}: {items[0].created_at} - {items[0].content[:50]}...")
        
        self.logger.info(f"Successfully scraped {len(items)} tweets for @{handle}")
        return items
    
    async def _scrape_via_api(
        self, 
        handle: str, 
        max_tweets: int,
        since_id: Optional[str] = None,
    ) -> List[ScrapedItem]:
        """Scrape using official Twitter API v2."""
        client = await self._get_client()
        
        # First, get user ID
        user_url = f"https://api.twitter.com/2/users/by/username/{handle}"
        headers = {"Authorization": f"Bearer {settings.TWITTER_BEARER_TOKEN}"}
        
        user_response = await client.get(user_url, headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        user_id = user_data["data"]["id"]
        
        # Then get tweets
        tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {
            "max_results": min(max_tweets, 100),
            "tweet.fields": "created_at,public_metrics,text",
            "expansions": "author_id",
            "user.fields": "name,username,profile_image_url",
        }
        if since_id:
            params["since_id"] = since_id
        
        tweets_response = await client.get(tweets_url, headers=headers, params=params)
        tweets_response.raise_for_status()
        tweets_data = tweets_response.json()
        
        items = []
        for tweet in tweets_data.get("data", []):
            item = ScrapedItem(
                id=tweet["id"],
                content=tweet["text"],
                source=f"twitter:@{handle}",
                url=f"https://twitter.com/{handle}/status/{tweet['id']}",
                created_at=datetime.fromisoformat(tweet["created_at"].replace("Z", "+00:00")),
                scraped_at=datetime.utcnow(),
                metadata={
                    "author_handle": handle,
                    "likes": tweet.get("public_metrics", {}).get("like_count", 0),
                    "retweets": tweet.get("public_metrics", {}).get("retweet_count", 0),
                    "replies": tweet.get("public_metrics", {}).get("reply_count", 0),
                    "method": "api",
                },
            )
            items.append(item)
        
        return items
    
    async def validate_target(self, target: str) -> bool:
        """Check if Twitter account exists and is accessible via RapidAPI."""
        target = target.lstrip("@")
        
        if not settings.RAPIDAPI_KEY:
            return True  # Assume valid if we can't check
        
        client = await self._get_client()
        headers = {
            "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
            "X-RapidAPI-Host": self.RAPIDAPI_HOST,
        }
        
        try:
            user_url = f"{self.RAPIDAPI_BASE_URL}/v2/UserByScreenName/"
            user_params = {"username": target}
            response = await client.get(user_url, headers=headers, params=user_params)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("user", {}).get("result", {}).get("rest_id") is not None
        except:
            pass
        
        return False
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
