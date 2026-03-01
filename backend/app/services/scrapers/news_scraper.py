from typing import List, Optional
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
import feedparser
import hashlib

from app.services.scrapers.base_scraper import BaseScraper, ScrapedItem


class NewsScraper(BaseScraper):
    """
    News scraper supporting RSS feeds and web scraping.
    
    Supports major crypto news sources:
    - CoinDesk
    - CoinTelegraph
    - The Block
    - Decrypt
    - And more via RSS
    """
    
    # Predefined crypto news sources with RSS feeds
    NEWS_SOURCES = {
        "coindesk": {
            "name": "CoinDesk",
            "rss": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "url": "https://coindesk.com",
        },
        "cointelegraph": {
            "name": "CoinTelegraph",
            "rss": "https://cointelegraph.com/rss",
            "url": "https://cointelegraph.com",
        },
        "theblock": {
            "name": "The Block",
            "rss": "https://www.theblock.co/rss.xml",
            "url": "https://theblock.co",
        },
        "decrypt": {
            "name": "Decrypt",
            "rss": "https://decrypt.co/feed",
            "url": "https://decrypt.co",
        },
        "bitcoinmagazine": {
            "name": "Bitcoin Magazine",
            "rss": "https://bitcoinmagazine.com/.rss/full/",
            "url": "https://bitcoinmagazine.com",
        },
    }
    
    def __init__(self):
        super().__init__("news")
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
        return self._client
    
    async def scrape(
        self, 
        target: str, 
        max_articles: int = 20,
        full_content: bool = False,
    ) -> List[ScrapedItem]:
        """
        Scrape news from a source.
        
        Args:
            target: Source ID (e.g., 'coindesk') or custom RSS URL
            max_articles: Maximum number of articles to fetch
            full_content: Whether to fetch full article content (slower)
        """
        # Check if it's a predefined source
        if target in self.NEWS_SOURCES:
            source_config = self.NEWS_SOURCES[target]
            rss_url = source_config["rss"]
            source_name = source_config["name"]
        else:
            # Treat as custom RSS URL
            rss_url = target
            source_name = "Custom"
        
        # Fetch and parse RSS feed
        items = await self._scrape_rss(rss_url, source_name, target, max_articles)
        
        # Optionally fetch full content for each article
        if full_content and items:
            items = await self._enrich_with_full_content(items)
        
        return items
    
    async def _scrape_rss(
        self, 
        rss_url: str, 
        source_name: str, 
        source_id: str,
        max_articles: int,
    ) -> List[ScrapedItem]:
        """Scrape articles from RSS feed."""
        client = await self._get_client()
        
        try:
            response = await client.get(rss_url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
        except Exception as e:
            self.logger.error(f"Failed to fetch RSS feed {rss_url}: {e}")
            return []
        
        items = []
        for entry in feed.entries[:max_articles]:
            try:
                # Parse publish date
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    created_at = datetime(*published[:6])
                else:
                    created_at = datetime.utcnow()
                
                # Generate unique ID
                article_id = entry.get("id") or entry.get("link")
                article_id = hashlib.sha256(article_id.encode()).hexdigest()[:16]
                
                # Get content
                content = ""
                if "content" in entry:
                    content = entry.content[0].get("value", "")
                elif "summary" in entry:
                    content = entry.summary
                elif "description" in entry:
                    content = entry.description
                
                # Clean HTML
                content = self._strip_html(content)
                
                # Extract image
                image_url = None
                if "media_content" in entry:
                    image_url = entry.media_content[0].get("url")
                elif "enclosures" in entry and entry.enclosures:
                    image_url = entry.enclosures[0].get("href")
                
                item = ScrapedItem(
                    id=article_id,
                    content=content,
                    source=f"news:{source_id}",
                    url=entry.get("link"),
                    created_at=created_at,
                    scraped_at=datetime.utcnow(),
                    metadata={
                        "title": entry.get("title", ""),
                        "source_id": source_id,
                        "source_name": source_name,
                        "author": entry.get("author", ""),
                        "image_url": image_url,
                        "tags": [tag.get("term") for tag in entry.get("tags", [])],
                    },
                )
                items.append(item)
                
            except Exception as e:
                self.logger.debug(f"Failed to parse RSS entry: {e}")
                continue
        
        return items
    
    async def _enrich_with_full_content(self, items: List[ScrapedItem]) -> List[ScrapedItem]:
        """Fetch full article content for each item."""
        client = await self._get_client()
        enriched = []
        
        for item in items:
            if not item.url:
                enriched.append(item)
                continue
            
            try:
                response = await client.get(item.url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Try common article content selectors
                content_selectors = [
                    "article",
                    ".article-content",
                    ".post-content",
                    ".entry-content",
                    "main",
                ]
                
                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        # Remove script and style elements
                        for tag in content_elem.find_all(["script", "style", "nav", "footer"]):
                            tag.decompose()
                        
                        full_content = self._clean_text(content_elem.get_text())
                        if len(full_content) > len(item.content):
                            item.content = full_content
                        break
                
            except Exception as e:
                self.logger.debug(f"Failed to fetch full content for {item.url}: {e}")
            
            enriched.append(item)
        
        return enriched
    
    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from content."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        return self._clean_text(soup.get_text())
    
    async def validate_target(self, target: str) -> bool:
        """Check if the news source is accessible."""
        if target in self.NEWS_SOURCES:
            rss_url = self.NEWS_SOURCES[target]["rss"]
        else:
            rss_url = target
        
        client = await self._get_client()
        try:
            response = await client.get(rss_url)
            return response.status_code == 200
        except:
            return False
    
    async def get_available_sources(self) -> dict:
        """Get list of predefined news sources."""
        return self.NEWS_SOURCES
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
