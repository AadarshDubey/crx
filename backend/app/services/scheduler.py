from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
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
from app.services.ai.embeddings import embedding_service
from app.services.ai.chunker import content_chunker
from app.services.pipeline_progress import pipeline_progress
from sqlalchemy import select, func, desc, and_
from app.services.cache import cache
from app.database.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class ScraperScheduler:
    """
    Scheduler for automated scraping jobs.
    
    Uses APScheduler to run periodic scraping tasks for
    Twitter accounts and news sources.
    """
    
    # Freshness thresholds — skip accounts/sources scraped within these windows
    TWEET_FRESHNESS_MINUTES = 30
    NEWS_FRESHNESS_MINUTES = 30
    STARTUP_FRESHNESS_MINUTES = 60  # skip entire initial pipeline if all data is this fresh
    
    # Concurrency limits for scraping (respects API rate limits)
    TWITTER_CONCURRENCY = 3
    NEWS_CONCURRENCY = 5
    
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
        
        # Full pipeline job - every hour
        self.scheduler.add_job(
            self._run_full_pipeline,
            trigger=IntervalTrigger(minutes=60),
            id="full_pipeline",
            name="Full Data Sync Pipeline",
            replace_existing=True,
        )
        
        # Run initial pipeline after startup
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
        """Run initial scrape on startup — skips if all data is fresh."""
        logger.info("Running initial scrape on startup...")
        await asyncio.sleep(3)  # Wait for app to fully start
        
        # Freshness gate: skip if all data was scraped recently
        if await self._all_data_fresh(self.STARTUP_FRESHNESS_MINUTES):
            logger.info(
                f"All data scraped within last {self.STARTUP_FRESHNESS_MINUTES}min — "
                "skipping initial pipeline"
            )
            return
        
        await self._run_full_pipeline()
    
    async def _all_data_fresh(self, max_age_minutes: int) -> bool:
        """Check if all tracked accounts and news were scraped within max_age_minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        try:
            async with async_session() as db:
                # Check if ANY active account has never been scraped or is stale
                result = await db.execute(
                    select(func.count(TrackedAccount.id)).where(
                        and_(
                            TrackedAccount.is_active == True,
                            (TrackedAccount.last_scraped_at == None) |
                            (TrackedAccount.last_scraped_at < cutoff)
                        )
                    )
                )
                stale_count = result.scalar() or 0
                
                if stale_count > 0:
                    logger.info(f"{stale_count} account(s) are stale, pipeline needed")
                    return False
                
                # Check if we have any recent news articles
                news_result = await db.execute(
                    select(func.count(NewsArticle.id)).where(
                        NewsArticle.scraped_at >= cutoff
                    )
                )
                recent_news = news_result.scalar() or 0
                if recent_news == 0:
                    logger.info("No recent news articles, pipeline needed")
                    return False
                
                return True
        except Exception as e:
            logger.warning(f"Freshness check failed: {e}, running pipeline")
            return False
    
    async def _run_full_pipeline(self):
        """
        Run the complete data sync pipeline with progress tracking.
        
        Steps:
          1. Initializing Data Sync
          2. Scraping Tweets
          3. Processing Tweet Sentiment (inline with step 2)
          4. Scraping News Feeds
          5. Processing News Sentiment (inline with step 4)
          6. Finalizing Sync
        """
        stats = {
            "tweets_saved": 0,
            "tweets_fetched": 0,
            "articles_saved": 0,
            "articles_fetched": 0,
            "sentiment_processed": 0,
            "errors": [],
        }
        
        try:
            # ─── Step 1: Initialize ───
            await pipeline_progress.start_pipeline()
            await asyncio.sleep(1)  # Brief pause for visual effect
            
            # ─── Step 2: Scrape Tweets ───
            await pipeline_progress.update_step(2, "Loading tracked accounts...", 0.0)
            tweets_saved = await self._scrape_twitter_with_progress(stats)
            stats["tweets_saved"] = tweets_saved
            
            # ─── Step 3: Tweet Sentiment Summary ───
            await pipeline_progress.update_step(
                3,
                f"Processed sentiment for {tweets_saved} new tweets",
                1.0,
            )
            await asyncio.sleep(1)
            
            # ─── Step 4: Scrape News ───
            await pipeline_progress.update_step(4, "Loading news sources...", 0.0)
            articles_saved = await self._scrape_news_with_progress(stats)
            stats["articles_saved"] = articles_saved
            
            # ─── Step 5: News Sentiment Summary ───
            await pipeline_progress.update_step(
                5,
                f"Processed sentiment for {articles_saved} new articles",
                1.0,
            )
            await asyncio.sleep(1)
            
            # ─── Step 6: Finalize ───
            await pipeline_progress.update_step(6, "Writing final data...", 0.5)
            await asyncio.sleep(1)
            
            await pipeline_progress.complete_pipeline(stats)
            logger.info(f"Full pipeline completed: {stats}")
            
            # Component 8: Warm cache after pipeline completes
            asyncio.create_task(self._warm_cache())
            
        except Exception as e:
            logger.error(f"Full pipeline failed: {e}", exc_info=True)
            await pipeline_progress.error_pipeline(str(e))
    
    async def _scrape_twitter_with_progress(self, stats: dict) -> int:
        """Scrape Twitter with concurrent fetching, freshness skip, and batch sentiment."""
        total_saved = 0
        
        try:
            # Get all tracked accounts
            account_data_list = []
            freshness_cutoff = datetime.utcnow() - timedelta(minutes=self.TWEET_FRESHNESS_MINUTES)
            
            async with async_session() as db:
                result = await db.execute(
                    select(TrackedAccount).where(TrackedAccount.is_active == True)
                )
                accounts = result.scalars().all()
                
                if not accounts:
                    await pipeline_progress.update_step(2, "No tracked accounts found", 1.0)
                    return 0
                
                for account in accounts:
                    account_data_list.append({
                        "id": account.id,
                        "handle": account.handle,
                        "name": account.name or account.handle,
                        "avatar_url": account.avatar_url,
                        "last_scraped_at": account.last_scraped_at,
                    })
            
            # Component 4: Filter out recently-scraped accounts
            stale_accounts = []
            skipped_count = 0
            for acc in account_data_list:
                if acc["last_scraped_at"] and acc["last_scraped_at"] > freshness_cutoff:
                    logger.info(f"Skipping @{acc['handle']} (scraped {int((datetime.utcnow() - acc['last_scraped_at']).total_seconds() / 60)}m ago)")
                    skipped_count += 1
                else:
                    stale_accounts.append(acc)
            
            total_accounts = len(account_data_list)
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count}/{total_accounts} fresh accounts")
            
            if not stale_accounts:
                await pipeline_progress.update_step(
                    2, f"All {total_accounts} accounts are fresh — skipped", 1.0
                )
                return 0
            
            logger.info(f"Scraping {len(stale_accounts)}/{total_accounts} stale accounts")
            
            # Component 3: Concurrent scraping with semaphore
            semaphore = asyncio.Semaphore(self.TWITTER_CONCURRENCY)
            completed = 0
            completed_lock = asyncio.Lock()
            
            async def scrape_one_account(account_data):
                nonlocal completed
                handle = account_data["handle"]
                
                async with semaphore:
                    try:
                        items = await self.twitter_scraper.scrape(
                            handle, max_tweets=20
                        )
                        return {"account": account_data, "items": items, "error": None}
                    except Exception as e:
                        logger.error(f"Failed to scrape @{handle}: {e}")
                        return {"account": account_data, "items": [], "error": str(e)[:80]}
                    finally:
                        async with completed_lock:
                            completed += 1
                            sub_progress = completed / len(stale_accounts)
                            await pipeline_progress.update_step(
                                2,
                                f"@{handle} ({completed}/{len(stale_accounts)} accounts)",
                                sub_progress,
                            )
            
            # Fire all scrapes concurrently (semaphore limits parallelism)
            scrape_results = await asyncio.gather(
                *[scrape_one_account(acc) for acc in stale_accounts],
                return_exceptions=True
            )
            
            # Process results: save tweets and batch-analyze sentiment
            for result in scrape_results:
                if isinstance(result, Exception):
                    stats["errors"].append(f"Twitter: {str(result)[:80]}")
                    continue
                
                if result["error"]:
                    stats["errors"].append(f"Twitter @{result['account']['handle']}: {result['error']}")
                    continue
                
                items = result["items"]
                account_data = result["account"]
                handle = account_data["handle"]
                account_name = account_data["name"]
                account_avatar = account_data["avatar_url"]
                account_id = account_data["id"]
                
                stats["tweets_fetched"] += len(items)
                if not items:
                    continue
                
                # Save tweets with batch sentiment
                async with async_session() as db:
                    # Pre-fetch existing tweet IDs
                    item_ids = [item.id for item in items]
                    existing_result = await db.execute(select(Tweet.id).where(Tweet.id.in_(item_ids)))
                    existing_ids = set(existing_result.scalars().all())
                    
                    new_items = [item for item in items if item.id not in existing_ids]
                    
                    if new_items:
                        # Component 2: Batch sentiment — one LLM call for all new tweets
                        texts_for_sentiment = [item.content for item in new_items]
                        try:
                            sentiment_results = await sentiment_analyzer.analyze_batch_efficient(texts_for_sentiment)
                        except Exception as e:
                            logger.warning(f"Batch sentiment failed for @{handle}: {e}, using fallback")
                            sentiment_results = [sentiment_analyzer._fallback_analysis(t) for t in texts_for_sentiment]
                        
                        stats["sentiment_processed"] += len(new_items)
                        
                        # Build tweet DB records
                        tweet_objects = []
                        for item, sentiment_result in zip(new_items, sentiment_results):
                            tweet = Tweet(
                                id=item.id,
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
                            tweet_objects.append((item, sentiment_result))
                        
                        # Chunk + embed tweets into vector store
                        try:
                            vector_store = get_vector_store()
                            all_chunks = []
                            for item, sentiment_result in tweet_objects:
                                chunks = content_chunker.chunk_tweet(
                                    tweet_id=item.id,
                                    text=item.content,
                                    metadata={
                                        "source": f"@{handle}",
                                        "source_type": "tweet",
                                        "type": "tweet",
                                        "sentiment": sentiment_result.label,
                                        "created_at": item.created_at.isoformat() if item.created_at else "",
                                        "url": item.url or "",
                                    }
                                )
                                all_chunks.extend(chunks)
                            
                            if all_chunks:
                                texts = [c.text for c in all_chunks]
                                embeddings = await embedding_service.embed_batch(texts)
                                docs = [{"content": c.text, "id": c.chunk_id, **c.metadata} for c in all_chunks]
                                ids = [c.chunk_id for c in all_chunks]
                                await vector_store.add_documents(docs, embeddings, ids)
                                logger.info(f"Embedded {len(all_chunks)} tweet chunks from @{handle}")
                        except Exception as emb_err:
                            logger.warning(f"Tweet embedding failed for @{handle}: {emb_err}")
                    
                    # Update last_scraped_at
                    account_result = await db.execute(
                        select(TrackedAccount).where(TrackedAccount.id == account_id)
                    )
                    account_to_update = account_result.scalar_one_or_none()
                    if account_to_update:
                        account_to_update.last_scraped_at = datetime.utcnow()
                    
                    await db.commit()
                    saved_count = len(new_items)
                    total_saved += saved_count
                    logger.info(f"Saved {saved_count} new tweets from @{handle}")
            
            # Final update for step 2
            await pipeline_progress.update_step(
                2,
                f"Done \u2014 {total_saved} new tweets from {len(stale_accounts)} accounts ({skipped_count} skipped)",
                1.0,
            )
            logger.info(f"Twitter scrape completed. Total new tweets: {total_saved}")
            
            if total_saved > 0:
                await cache.invalidate("tweets:*")
            
        except Exception as e:
            logger.error(f"Twitter scrape job failed: {e}", exc_info=True)
            stats["errors"].append(f"Twitter: {str(e)[:100]}")
        
        return total_saved
    
    async def _scrape_news_with_progress(self, stats: dict) -> int:
        """Scrape news with concurrent fetching and batch sentiment."""
        total_saved = 0
        
        try:
            sources = list(self.news_scraper.NEWS_SOURCES.keys())
            source_names = {k: v["name"] for k, v in self.news_scraper.NEWS_SOURCES.items()}
            total_sources = len(sources)
            
            # Component 3: Concurrent RSS fetching with semaphore
            semaphore = asyncio.Semaphore(self.NEWS_CONCURRENCY)
            completed = 0
            completed_lock = asyncio.Lock()
            
            async def fetch_one_source(source_id):
                nonlocal completed
                async with semaphore:
                    try:
                        items = await self.news_scraper.scrape(source_id, max_articles=15)
                        return {"source_id": source_id, "items": items, "error": None}
                    except Exception as e:
                        return {"source_id": source_id, "items": [], "error": str(e)[:80]}
                    finally:
                        async with completed_lock:
                            completed += 1
                            await pipeline_progress.update_step(
                                4,
                                f"{source_names.get(source_id, source_id)} ({completed}/{total_sources} sources)",
                                completed / total_sources,
                            )
            
            fetch_results = await asyncio.gather(
                *[fetch_one_source(src) for src in sources],
                return_exceptions=True
            )
            
            # Process all fetched results
            async with async_session() as db:
                for result in fetch_results:
                    if isinstance(result, Exception):
                        stats["errors"].append(f"News: {str(result)[:80]}")
                        continue
                    
                    if result["error"]:
                        source_name = source_names.get(result["source_id"], result["source_id"])
                        stats["errors"].append(f"News {source_name}: {result['error']}")
                        continue
                    
                    source_id = result["source_id"]
                    items = result["items"]
                    stats["articles_fetched"] += len(items)
                    
                    if not items:
                        continue
                    
                    # Pre-fetch existing article URLs
                    item_urls = [item.url for item in items if item.url]
                    existing_urls = set()
                    if item_urls:
                        existing_result = await db.execute(select(NewsArticle.url).where(NewsArticle.url.in_(item_urls)))
                        existing_urls = set(existing_result.scalars().all())
                    
                    new_items = [item for item in items if item.url not in existing_urls]
                    
                    if new_items:
                        # Component 2: Batch sentiment for all new articles from this source
                        texts_for_sentiment = [
                            f"{item.metadata.get('title', '')} {item.content[:500]}"
                            for item in new_items
                        ]
                        try:
                            sentiment_results = await sentiment_analyzer.analyze_batch_efficient(texts_for_sentiment)
                        except Exception as e:
                            logger.warning(f"Batch sentiment failed for {source_id}: {e}, using fallback")
                            sentiment_results = [sentiment_analyzer._fallback_analysis(t) for t in texts_for_sentiment]
                        
                        stats["sentiment_processed"] += len(new_items)
                        
                        # Build article DB records + collect for vector embedding
                        articles_for_embedding = []
                        for item, sentiment_result in zip(new_items, sentiment_results):
                            title = item.metadata.get("title", "")
                            article = NewsArticle(
                                id=item.id,
                                title=title,
                                url=item.url,
                                source_id=source_id,
                                source_name=item.metadata.get("source_name", source_id),
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
                            articles_for_embedding.append((item, title, sentiment_result))
                        
                        # Chunk + embed articles into vector store
                        try:
                            vector_store = get_vector_store()
                            all_chunks = []
                            for item, title, sentiment_result in articles_for_embedding:
                                chunks = content_chunker.chunk_article(
                                    article_id=item.id,
                                    title=title,
                                    content=item.content or "",
                                    metadata={
                                        "source": source_id,
                                        "source_name": item.metadata.get("source_name", source_id),
                                        "source_type": "news",
                                        "type": "news",
                                        "sentiment": sentiment_result.label,
                                        "created_at": item.created_at.isoformat() if item.created_at else "",
                                        "url": item.url or "",
                                        "title": title,
                                    }
                                )
                                all_chunks.extend(chunks)
                            
                            if all_chunks:
                                texts = [c.text for c in all_chunks]
                                embeddings = await embedding_service.embed_batch(texts)
                                docs = [{"content": c.text, "id": c.chunk_id, **c.metadata} for c in all_chunks]
                                ids = [c.chunk_id for c in all_chunks]
                                await vector_store.add_documents(docs, embeddings, ids)
                                logger.info(f"Embedded {len(all_chunks)} chunks from {len(articles_for_embedding)} articles ({source_id})")
                        except Exception as emb_err:
                            logger.warning(f"Article embedding failed for {source_id}: {emb_err}")
                        
                        total_saved += len(new_items)
                
                await db.commit()
            
            # Final update for step 4
            await pipeline_progress.update_step(
                4,
                f"Done \u2014 {total_saved} new articles from {total_sources} sources",
                1.0,
            )
            logger.info(f"News scrape completed. Total new articles: {total_saved}")
            
            if total_saved > 0:
                await cache.invalidate("news:*")
            
        except Exception as e:
            logger.error(f"News scrape job failed: {e}", exc_info=True)
            stats["errors"].append(f"News: {str(e)[:100]}")
        
        return total_saved
    
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
                # Run full pipeline for visibility
                asyncio.create_task(self._run_full_pipeline())
                return {"status": "pipeline_started", "type": "full_pipeline"}
        
        elif target_type == "news":
            if target:
                items = await self.news_scraper.scrape(target)
                return {"scraped": len(items), "target": target}
            else:
                asyncio.create_task(self._run_full_pipeline())
                return {"status": "pipeline_started", "type": "full_pipeline"}
        
        elif target_type == "all":
            asyncio.create_task(self._run_full_pipeline())
            return {"status": "pipeline_started", "type": "full_pipeline"}
        
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
    
    async def _warm_cache(self):
        """Pre-populate Redis cache with commonly-requested data after pipeline."""
        try:
            logger.info("Warming cache after pipeline...")
            
            async with async_session() as db:
                # Warm tweets:stats:24h
                since_24h = datetime.utcnow() - timedelta(hours=24)
                
                total_result = await db.execute(select(func.count(Tweet.id)))
                total_tweets = total_result.scalar() or 0
                
                range_result = await db.execute(
                    select(func.count(Tweet.id)).where(Tweet.tweet_created_at >= since_24h)
                )
                tweets_24h = range_result.scalar() or 0
                
                stats_data = {
                    "total_tweets": total_tweets,
                    "tweets_24h": tweets_24h,
                    "time_range": "24h",
                }
                await cache.set("tweets:stats:24h", stats_data, ttl=120)
                
                # Warm tweets:recent:5
                recent_result = await db.execute(
                    select(Tweet).order_by(desc(Tweet.tweet_created_at)).limit(5)
                )
                recent_tweets = recent_result.scalars().all()
                recent_data = [t.to_dict() for t in recent_tweets]
                await cache.set("tweets:recent:5", recent_data, ttl=120)
                
            logger.info("Cache warmed successfully")
        except Exception as e:
            logger.warning(f"Cache warm-up failed (non-critical): {e}")


# Singleton instance
scraper_scheduler = ScraperScheduler()
