from abc import ABC, abstractmethod
from typing import List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScrapedItem:
    """Base class for scraped content."""
    id: str
    content: str
    source: str
    url: Optional[str]
    created_at: datetime
    scraped_at: datetime
    metadata: dict


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"scraper.{name}")
        self._rate_limit_delay = 1.0  # seconds between requests
        self._max_retries = 3
    
    @abstractmethod
    async def scrape(self, target: str, **kwargs) -> List[ScrapedItem]:
        """
        Scrape content from the target.
        
        Args:
            target: The target to scrape (e.g., Twitter handle, news URL)
            **kwargs: Additional scraping parameters
            
        Returns:
            List of scraped items
        """
        pass
    
    @abstractmethod
    async def validate_target(self, target: str) -> bool:
        """Validate that the target exists and is accessible."""
        pass
    
    async def scrape_with_retry(self, target: str, **kwargs) -> List[ScrapedItem]:
        """Scrape with automatic retry on failure."""
        for attempt in range(self._max_retries):
            try:
                return await self.scrape(target, **kwargs)
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {target}: {e}")
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._rate_limit_delay * (attempt + 1))
                else:
                    self.logger.error(f"All retries failed for {target}")
                    raise
        return []
    
    async def scrape_multiple(self, targets: List[str], **kwargs) -> dict[str, List[ScrapedItem]]:
        """Scrape multiple targets with rate limiting."""
        results = {}
        for target in targets:
            try:
                items = await self.scrape_with_retry(target, **kwargs)
                results[target] = items
                await asyncio.sleep(self._rate_limit_delay)
            except Exception as e:
                self.logger.error(f"Failed to scrape {target}: {e}")
                results[target] = []
        return results
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        # Remove excessive whitespace
        text = " ".join(text.split())
        return text.strip()
    
    def _generate_id(self, *args) -> str:
        """Generate a unique ID from components."""
        import hashlib
        combined = "_".join(str(arg) for arg in args)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
