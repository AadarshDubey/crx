from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging
import asyncio

from app.config import settings
from app.database.connection import async_session
from app.models.account import TrackedAccount
from app.models.tweet import Tweet
from app.models.news import NewsArticle
from app.services.scrapers.twitter_scraper import TwitterScraper
from app.services.scrapers.news_scraper import NewsScraper
from app.services.ai.sentiment import sentiment_analyzer
from sqlalchemy import select

logger = logging.getLogger(__name__)


class ScraperScheduler:
    """
    Scheduler for automated scraping jobs.
    
    Uses APScheduler to run periodic scraping tasks for
    Twitter accounts and news sources.
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.twitter_scraper = TwitterScraper()
        self.news_scraper = NewsScraper()
        self._is_running = False
    
    def start(self):
        """Start the scheduler with default jobs."""
        if self._is_running:
            logger.warning("Scheduler already running")
            return
        
        # Twitter scraping job - every hour
        self.scheduler.add_job(
            self._scrape_twitter_job,
            trigger=IntervalTrigger(minutes=60),
            id="twitter_scrape",
            name="Twitter Scrape Job",
            replace_existing=True,
        )
        
        # News scraping job - every hour
        self.scheduler.add_job(
            self._scrape_news_job,
            trigger=IntervalTrigger(minutes=60),
            id="news_scrape",
            name="News Scrape Job",
            replace_existing=True,
        )
        
        # Sentiment analysis job (process unanalyzed content)
        self.scheduler.add_job(
            self._sentiment_analysis_job,
            trigger=IntervalTrigger(minutes=15),
            id="sentiment_analysis",
            name="Sentiment Analysis Job",
            replace_existing=True,
        )
        
        # Run initial scrape after startup
        self.scheduler.add_job(
            self._initial_scrape,
            trigger='date',
            run_date=datetime.now(),
            id="initial_scrape",
            name="Initial Scrape on Startup",
        )
        
        self.scheduler.start()
        self._is_running = True
        logger.info("Scheduler started - scraping every hour")
    
    def stop(self):
        """Stop the scheduler."""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Scheduler stopped")
    
    async def _initial_scrape(self):
        """Run initial scrape on startup."""
        logger.info("Running initial scrape on startup...")
        await asyncio.sleep(5)  # Wait for app to fully start
        await self._scrape_twitter_job()
        await self._scrape_news_job()
        logger.info("Initial scrape completed")
    
    async def _scrape_twitter_job(self):
        """Job to scrape all tracked Twitter accounts."""
        logger.info("Starting Twitter scrape job")
        
        try:
            # First, get all account data in a separate session to avoid lazy loading issues
            account_data_list = []
            async with async_session() as db:
                result = await db.execute(
                    select(TrackedAccount).where(TrackedAccount.is_active == True)
                )
                accounts = result.scalars().all()
                
                if not accounts:
                    logger.info("No tracked accounts found")
                    return
                
                # Extract all data upfront to avoid lazy loading issues after rollback
                for account in accounts:
                    account_data_list.append({
                        "id": account.id,
                        "handle": account.handle,
                        "name": account.name or account.handle,
                        "avatar_url": account.avatar_url,
                    })
            
            logger.info(f"Scraping {len(account_data_list)} tracked accounts")
            total_saved = 0
            
            # Process each account in its own session to isolate failures
            for account_data in account_data_list:
                handle = account_data["handle"]
                account_name = account_data["name"]
                account_avatar = account_data["avatar_url"]
                account_id = account_data["id"]
                
                try:
                    items = await self.twitter_scraper.scrape(
                        handle, 
                        max_tweets=20
                    )
                    
                    logger.info(f"Fetched {len(items)} tweets from @{handle}")
                    
                    if not items:
                        continue
                    
                    # Save tweets in a fresh session
                    async with async_session() as db:
                        saved_count = 0
                        for item in items:
                            tweet_id = item.id
                            
                            # Check if tweet already exists
                            existing = await db.execute(
                                select(Tweet.id).where(Tweet.id == tweet_id)
                            )
                            if existing.scalar_one_or_none():
                                continue
                            
                            # Analyze sentiment
                            sentiment_result = await sentiment_analyzer.analyze(item.content)
                            
                            tweet = Tweet(
                                id=tweet_id,
                                content=item.content,
                                author_handle=handle,
                                author_name=item.metadata.get("author_name", account_name),
                                author_avatar=item.metadata.get("author_avatar", account_avatar),
                                tweet_created_at=item.created_at,
                                likes=item.metadata.get("likes", 0),
                                retweets=item.metadata.get("retweets", 0),
                                replies=item.metadata.get("replies", 0),
                                sentiment_score=sentiment_result.score,
                                sentiment_label=sentiment_result.label,
                            )
                            db.add(tweet)
                            saved_count += 1
                        
                        # Update last_scraped_at
                        account_result = await db.execute(
                            select(TrackedAccount).where(TrackedAccount.id == account_id)
                        )
                        account_to_update = account_result.scalar_one_or_none()
                        if account_to_update:
                            account_to_update.last_scraped_at = datetime.utcnow()
                        
                        await db.commit()
                        total_saved += saved_count
                        logger.info(f"Saved {saved_count} new tweets from @{handle}")
                        
                except Exception as e:
                    logger.error(f"Failed to scrape @{handle}: {e}")
                    # Continue to next account - no rollback needed as each account has its own session
            
            logger.info(f"Twitter scrape job completed. Total new tweets: {total_saved}")
            
        except Exception as e:
            logger.error(f"Twitter scrape job failed: {e}", exc_info=True)
    
    async def _scrape_news_job(self):
        """Job to scrape all news sources."""
        logger.info("Starting news scrape job")
        
        try:
            async with async_session() as db:
                sources = list(self.news_scraper.NEWS_SOURCES.keys())
                total_saved = 0
                
                for source_id in sources:
                    try:
                        items = await self.news_scraper.scrape(source_id, max_articles=15)
                        logger.info(f"Fetched {len(items)} items from {source_id}")
                        
                        if not items:
                            continue
                        
                        saved_count = 0
                        for item in items:
                            # Check if article already exists by URL
                            existing = await db.execute(
                                select(NewsArticle.id).where(NewsArticle.url == item.url)
                            )
                            if existing.scalar_one_or_none():
                                continue
                            
                            # Get data from ScrapedItem
                            title = item.metadata.get("title", "")
                            source_name = item.metadata.get("source_name", source_id)
                            
                            # Analyze sentiment
                            content_for_sentiment = f"{title} {item.content[:500]}"
                            sentiment_result = await sentiment_analyzer.analyze(content_for_sentiment)
                            
                            article = NewsArticle(
                                id=item.id,  # Required primary key from ScrapedItem
                                title=title,
                                url=item.url,
                                source_id=source_id,
                                source_name=source_name,
                                excerpt=item.content[:300] if item.content else "",
                                content=item.content,
                                image_url=item.metadata.get("image_url"),
                                author=item.metadata.get("author"),
                                published_at=item.created_at,
                                scraped_at=datetime.utcnow(),
                                category=None,
                                sentiment_score=sentiment_result.score,
                                sentiment_label=sentiment_result.label,
                            )
                            db.add(article)
                            saved_count += 1
                        
                        await db.commit()
                        total_saved += saved_count
                        logger.info(f"Saved {saved_count} new articles from {source_id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to scrape {source_id}: {e}", exc_info=True)
                        await db.rollback()
                
                logger.info(f"News scrape job completed. Total new articles: {total_saved}")
            
        except Exception as e:
            logger.error(f"News scrape job failed: {e}", exc_info=True)
    
    async def _sentiment_analysis_job(self):
        """Job to analyze sentiment of unprocessed content."""
        logger.info("Starting sentiment analysis job")
        
        try:
            async with async_session() as db:
                # Find tweets without sentiment
                result = await db.execute(
                    select(Tweet).where(Tweet.sentiment_label == None).limit(50)
                )
                tweets = result.scalars().all()
                
                for tweet in tweets:
                    try:
                        sentiment_result = await sentiment_analyzer.analyze(tweet.content)
                        tweet.sentiment_score = sentiment_result.score
                        tweet.sentiment_label = sentiment_result.label
                    except Exception as e:
                        logger.error(f"Failed to analyze tweet {tweet.id}: {e}")
                
                # Find articles without sentiment
                result = await db.execute(
                    select(NewsArticle).where(NewsArticle.sentiment_label == None).limit(50)
                )
                articles = result.scalars().all()
                
                for article in articles:
                    try:
                        content = f"{article.title} {article.summary or ''}"
                        sentiment_result = await sentiment_analyzer.analyze(content)
                        article.sentiment_score = sentiment_result.score
                        article.sentiment_label = sentiment_result.label
                    except Exception as e:
                        logger.error(f"Failed to analyze article {article.id}: {e}")
                
                await db.commit()
                logger.info(f"Sentiment analysis completed: {len(tweets)} tweets, {len(articles)} articles")
            
        except Exception as e:
            logger.error(f"Sentiment analysis job failed: {e}")
    
    async def trigger_scrape(self, target_type: str, target: str = None):
        """
        Manually trigger a scrape.
        
        Args:
            target_type: 'twitter' or 'news'
            target: Specific account/source, or None for all
        """
        if target_type == "twitter":
            if target:
                items = await self.twitter_scraper.scrape(target)
                return {"scraped": len(items), "target": target}
            else:
                await self._scrape_twitter_job()
                return {"status": "completed", "type": "all_twitter"}
        
        elif target_type == "news":
            if target:
                items = await self.news_scraper.scrape(target)
                return {"scraped": len(items), "target": target}
            else:
                await self._scrape_news_job()
                return {"status": "completed", "type": "all_news"}
        
        return {"error": "Invalid target_type"}
    
    def get_job_status(self) -> dict:
        """Get status of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            })
        return {"jobs": jobs, "running": self._is_running}


# Singleton instance
scraper_scheduler = ScraperScheduler()
