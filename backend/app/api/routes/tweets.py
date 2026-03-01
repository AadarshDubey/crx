from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.database.connection import get_db
from app.models.tweet import Tweet
from app.models.account import TrackedAccount
from app.services.scrapers.twitter_scraper import TwitterScraper
from app.services.ai.embeddings import embedding_service
from app.database.vector_store import get_vector_store
from app.services.cache import cache

router = APIRouter()

# Initialize scraper
twitter_scraper = TwitterScraper()

# Cache TTLs
TWEETS_CACHE_TTL = 120  # 2 minutes


class ScrapeRequest(BaseModel):
    """Request model for scraping tweets."""
    handle: str
    since: Optional[datetime] = None  # Start date
    until: Optional[datetime] = None  # End date
    max_tweets: int = 50
    include_replies: bool = False
    include_retweets: bool = False
    store_embeddings: bool = True


class AddAccountRequest(BaseModel):
    """Request model for adding a tracked account."""
    handle: str
    name: Optional[str] = None
    category: str = "general"
    priority: int = 1
    scrape_replies: bool = False
    scrape_retweets: bool = False


@router.get("/")
async def get_tweets(
    db: AsyncSession = Depends(get_db),
    account: Optional[str] = Query(None, description="Filter by Twitter account handle"),
    limit: int = Query(50, ge=1, le=100, description="Number of tweets to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment: positive, negative, neutral"),
    since: Optional[datetime] = Query(None, description="Filter tweets after this date"),
    until: Optional[datetime] = Query(None, description="Filter tweets before this date"),
):
    """Get scraped tweets from database with optional filtering."""
    
    # Build query
    query = select(Tweet).order_by(desc(Tweet.tweet_created_at))
    count_query = select(func.count(Tweet.id))
    
    # Apply filters
    filters = []
    if account:
        filters.append(Tweet.author_handle == account.lstrip("@"))
    if sentiment:
        filters.append(Tweet.sentiment_label == sentiment)
    if since:
        filters.append(Tweet.tweet_created_at >= since)
    if until:
        filters.append(Tweet.tweet_created_at <= until)
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    tweets = result.scalars().all()
    
    return {
        "tweets": [tweet.to_dict() for tweet in tweets],
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "account": account,
            "sentiment": sentiment,
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
        }
    }


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    time_range: str = Query("24h", description="Time range: 1h, 6h, 24h, 7d, 30d"),
):
    """Get dashboard statistics including tweet counts, sentiment breakdown, and tracked accounts."""
    
    # Check cache first
    cache_key = f"tweets:stats:{time_range}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Parse time range
    time_deltas = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    delta = time_deltas.get(time_range, timedelta(hours=24))
    since_time = datetime.utcnow() - delta
    
    # Total tweets in DB
    total_result = await db.execute(select(func.count(Tweet.id)))
    total_tweets = total_result.scalar() or 0
    
    # Tweets in time range
    tweets_in_range_result = await db.execute(
        select(func.count(Tweet.id)).where(Tweet.tweet_created_at >= since_time)
    )
    tweets_in_range = tweets_in_range_result.scalar() or 0
    
    # Sentiment breakdown in time range
    sentiment_query = select(
        Tweet.sentiment_label,
        func.count(Tweet.id)
    ).where(
        and_(
            Tweet.tweet_created_at >= since_time,
            Tweet.sentiment_label.isnot(None)
        )
    ).group_by(Tweet.sentiment_label)
    
    sentiment_result = await db.execute(sentiment_query)
    sentiment_counts = {row[0]: row[1] for row in sentiment_result.all()}
    
    total_with_sentiment = sum(sentiment_counts.values()) or 1  # Avoid division by zero
    bullish_count = sentiment_counts.get("positive", 0) + sentiment_counts.get("bullish", 0)
    bearish_count = sentiment_counts.get("negative", 0) + sentiment_counts.get("bearish", 0)
    neutral_count = sentiment_counts.get("neutral", 0)
    
    bullish_pct = round((bullish_count / total_with_sentiment) * 100, 1)
    bearish_pct = round((bearish_count / total_with_sentiment) * 100, 1)
    neutral_pct = round((neutral_count / total_with_sentiment) * 100, 1)
    
    # Tracked accounts count
    accounts_result = await db.execute(
        select(func.count(TrackedAccount.id)).where(TrackedAccount.is_active == True)
    )
    tracked_accounts = accounts_result.scalar() or 0
    
    # Calculate sentiment change vs previous period
    prev_since = since_time - delta
    prev_sentiment_query = select(
        Tweet.sentiment_label,
        func.count(Tweet.id)
    ).where(
        and_(
            Tweet.tweet_created_at >= prev_since,
            Tweet.tweet_created_at < since_time,
            Tweet.sentiment_label.isnot(None)
        )
    ).group_by(Tweet.sentiment_label)
    
    prev_result = await db.execute(prev_sentiment_query)
    prev_counts = {row[0]: row[1] for row in prev_result.all()}
    prev_total = sum(prev_counts.values()) or 1
    prev_bullish = prev_counts.get("positive", 0) + prev_counts.get("bullish", 0)
    prev_bullish_pct = (prev_bullish / prev_total) * 100
    
    sentiment_change = round(bullish_pct - prev_bullish_pct, 1)
    
    response = {
        "total_tweets": total_tweets,
        "tweets_24h": tweets_in_range,
        "bullish_percentage": bullish_pct,
        "bearish_percentage": bearish_pct,
        "neutral_percentage": neutral_pct,
        "tracked_accounts": tracked_accounts,
        "sentiment_change": sentiment_change,
        "time_range": time_range,
    }
    
    # Cache the response
    await cache.set(cache_key, response, ttl=TWEETS_CACHE_TTL)
    
    return response


@router.get("/recent")
async def get_recent_tweets(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(5, ge=1, le=20, description="Number of recent tweets"),
):
    """Get the most recent tweets."""
    
    # Check cache first
    cache_key = f"tweets:recent:{limit}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    query = select(Tweet).order_by(desc(Tweet.tweet_created_at)).limit(limit)
    result = await db.execute(query)
    tweets = result.scalars().all()
    
    response = [tweet.to_dict() for tweet in tweets]
    
    # Cache the response
    await cache.set(cache_key, response, ttl=TWEETS_CACHE_TTL)
    
    return response


@router.get("/sentiment-timeline")
async def get_sentiment_timeline(
    db: AsyncSession = Depends(get_db),
    time_range: str = Query("24h", description="Time range: 1h, 6h, 24h, 7d, 30d"),
):
    """Get sentiment data over time for charts."""
    
    # Parse time range and determine interval
    time_configs = {
        "1h": (timedelta(hours=1), timedelta(minutes=5), "%H:%M"),
        "6h": (timedelta(hours=6), timedelta(minutes=30), "%H:%M"),
        "24h": (timedelta(hours=24), timedelta(hours=2), "%H:%M"),
        "7d": (timedelta(days=7), timedelta(hours=12), "%m/%d"),
        "30d": (timedelta(days=30), timedelta(days=1), "%m/%d"),
    }
    
    delta, interval, time_fmt = time_configs.get(time_range, time_configs["24h"])
    since_time = datetime.utcnow() - delta
    
    # Get all tweets in range with sentiment
    tweets_query = select(
        Tweet.tweet_created_at,
        Tweet.sentiment_label,
        Tweet.sentiment_score
    ).where(
        and_(
            Tweet.tweet_created_at >= since_time,
            Tweet.sentiment_label.isnot(None)
        )
    ).order_by(Tweet.tweet_created_at)
    
    result = await db.execute(tweets_query)
    tweets = result.all()
    
    # Group by time intervals
    timeline_data = []
    current_time = since_time
    end_time = datetime.utcnow()
    
    while current_time < end_time:
        interval_end = current_time + interval
        
        # Count sentiments in this interval
        interval_tweets = [t for t in tweets if current_time <= t[0] < interval_end]
        
        if interval_tweets:
            bullish = sum(1 for t in interval_tweets if t[1] in ["positive", "bullish"])
            bearish = sum(1 for t in interval_tweets if t[1] in ["negative", "bearish"])
            neutral = sum(1 for t in interval_tweets if t[1] == "neutral")
            total = len(interval_tweets)
            
            timeline_data.append({
                "timestamp": current_time.isoformat(),
                "time_label": current_time.strftime(time_fmt),
                "bullish": round((bullish / total) * 100) if total > 0 else 50,
                "bearish": round((bearish / total) * 100) if total > 0 else 50,
                "neutral": round((neutral / total) * 100) if total > 0 else 0,
                "total_tweets": total,
            })
        else:
            # No tweets in this interval, use neutral values
            timeline_data.append({
                "timestamp": current_time.isoformat(),
                "time_label": current_time.strftime(time_fmt),
                "bullish": 50,
                "bearish": 50,
                "neutral": 0,
                "total_tweets": 0,
            })
        
        current_time = interval_end
    
    return timeline_data


@router.get("/accounts")
async def get_tracked_accounts(db: AsyncSession = Depends(get_db)):
    """Get list of Twitter accounts being tracked from database."""
    
    query = select(TrackedAccount).where(TrackedAccount.is_active == True).order_by(TrackedAccount.priority.desc())
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    return {
        "accounts": [account.to_dict() for account in accounts],
        "total": len(accounts),
    }


@router.post("/accounts")
async def add_tracked_account(
    request: AddAccountRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a new Twitter account to track."""
    
    handle = request.handle.lstrip("@")
    
    # Check if already exists (including inactive)
    result = await db.execute(
        select(TrackedAccount).where(TrackedAccount.handle == handle)
    )
    existing_account = result.scalar_one_or_none()
    
    if existing_account:
        # If it's already active, return error
        if existing_account.is_active:
            raise HTTPException(status_code=400, detail=f"Account @{handle} is already being tracked")
        
        # Reactivate and update fields
        existing_account.name = request.name
        existing_account.category = request.category
        existing_account.priority = request.priority
        existing_account.scrape_replies = request.scrape_replies
        existing_account.scrape_retweets = request.scrape_retweets
        existing_account.is_active = True
        
        await db.commit()
        await db.refresh(existing_account)
        return existing_account.to_dict()
    
    # Create new tracked account
    account = TrackedAccount(
        handle=handle,
        name=request.name,
        category=request.category,
        priority=request.priority,
        scrape_replies=request.scrape_replies,
        scrape_retweets=request.scrape_retweets,
        is_active=True,
    )
    
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account.to_dict()


@router.delete("/accounts/{handle}")
async def remove_tracked_account(
    handle: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a Twitter account from tracking (soft delete - sets inactive)."""
    
    handle = handle.lstrip("@")
    
    result = await db.execute(
        select(TrackedAccount).where(TrackedAccount.handle == handle)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail=f"Account @{handle} not found")
    
    account.is_active = False
    await db.commit()
    
    return {"message": f"Account @{handle} removed from tracking list"}


@router.post("/accounts/{handle}/scrape")
async def scrape_single_account(
    handle: str,
    db: AsyncSession = Depends(get_db),
):
    """Trigger scraping for a specific tracked account."""
    
    handle = handle.lstrip("@")
    
    # Verify account exists and is active
    result = await db.execute(
        select(TrackedAccount).where(TrackedAccount.handle == handle)
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail=f"Account @{handle} not found")
    
    if not account.is_active:
        raise HTTPException(status_code=400, detail=f"Account @{handle} is not active")
    
    try:
        # Scrape tweets for this account
        scraped_items = await twitter_scraper.scrape(
            target=handle,
            max_tweets=20,
            include_replies=account.scrape_replies,
            include_retweets=account.scrape_retweets,
        )
        
        # Store tweets in database
        tweets_stored = 0
        for item in scraped_items:
            # Check if tweet already exists
            existing = await db.execute(select(Tweet).where(Tweet.id == item.id))
            if existing.scalar_one_or_none():
                continue
            
            # Create tweet record
            tweet = Tweet(
                id=item.id,
                content=item.content,
                author_handle=handle,
                author_name=item.metadata.get("author_name"),
                author_avatar=item.metadata.get("author_avatar"),
                likes=item.metadata.get("likes", 0),
                retweets=item.metadata.get("retweets", 0),
                replies=item.metadata.get("replies", 0),
                tweet_created_at=item.created_at,
                scraped_at=item.scraped_at,
                url=item.url,
                is_retweet=item.metadata.get("is_retweet", False),
                is_reply=item.metadata.get("is_reply", False),
            )
            
            db.add(tweet)
            tweets_stored += 1
        
        await db.commit()
        
        # Update account last scraped time
        account.last_scraped_at = datetime.utcnow()
        await db.commit()
        
        return {
            "message": f"Successfully scraped @{handle}",
            "tweets_found": len(scraped_items),
            "tweets_stored": tweets_stored,
        }
        
    except Exception as e:
        return {
            "message": f"Scraping @{handle} completed with issues: {str(e)}",
            "tweets_found": 0,
            "tweets_stored": 0,
        }


@router.get("/accounts/{handle}/stats")
async def get_account_stats(
    handle: str,
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for a specific tracked account."""
    
    handle = handle.lstrip("@")
    
    # Get tweet count
    count_result = await db.execute(
        select(func.count(Tweet.id)).where(Tweet.author_handle == handle)
    )
    tweet_count = count_result.scalar() or 0
    
    # Get sentiment breakdown
    sentiment_query = select(
        Tweet.sentiment_label,
        func.count(Tweet.id)
    ).where(
        and_(Tweet.author_handle == handle, Tweet.sentiment_label.isnot(None))
    ).group_by(Tweet.sentiment_label)
    
    sentiment_result = await db.execute(sentiment_query)
    sentiment_breakdown = {row[0]: row[1] for row in sentiment_result.all()}
    
    # Get latest tweet
    latest_result = await db.execute(
        select(Tweet).where(Tweet.author_handle == handle).order_by(desc(Tweet.tweet_created_at)).limit(1)
    )
    latest_tweet = latest_result.scalar_one_or_none()
    
    return {
        "handle": handle,
        "total_tweets": tweet_count,
        "sentiment_breakdown": sentiment_breakdown,
        "latest_tweet": latest_tweet.to_dict() if latest_tweet else None,
    }


@router.get("/{tweet_id}")
async def get_tweet_by_id(
    tweet_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific tweet by ID with full details."""
    
    result = await db.execute(select(Tweet).where(Tweet.id == tweet_id))
    tweet = result.scalar_one_or_none()
    
    if not tweet:
        raise HTTPException(status_code=404, detail=f"Tweet {tweet_id} not found")
    
    return tweet.to_dict()


@router.post("/scrape")
async def scrape_tweets(
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Scrape tweets from a Twitter account with date range filtering.
    
    - **handle**: Twitter handle (with or without @)
    - **since**: Start date (optional) - only get tweets after this date
    - **until**: End date (optional) - only get tweets before this date  
    - **max_tweets**: Maximum tweets to fetch (default 50)
    - **include_replies**: Include reply tweets
    - **include_retweets**: Include retweets
    - **store_embeddings**: Store embeddings for RAG search
    """
    
    handle = request.handle.lstrip("@")
    
    try:
        # Scrape tweets
        scraped_items = await twitter_scraper.scrape(
            target=handle,
            max_tweets=request.max_tweets,
            include_replies=request.include_replies,
            include_retweets=request.include_retweets,
        )
        
        if not scraped_items:
            return {
                "status": "success",
                "message": f"No tweets found for @{handle}",
                "tweets_scraped": 0,
                "tweets_stored": 0,
                "embeddings_stored": 0,
            }
        
        # Filter by date range if specified
        filtered_items = []
        for item in scraped_items:
            if request.since and item.created_at < request.since:
                continue
            if request.until and item.created_at > request.until:
                continue
            filtered_items.append(item)
        
        # Store tweets in database
        tweets_stored = 0
        tweets_to_embed = []
        
        for item in filtered_items:
            # Check if tweet already exists
            existing = await db.execute(select(Tweet).where(Tweet.id == item.id))
            if existing.scalar_one_or_none():
                continue
            
            # Create tweet record
            tweet = Tweet(
                id=item.id,
                content=item.content,
                author_handle=handle,
                author_name=item.metadata.get("author_name"),
                author_avatar=item.metadata.get("author_avatar"),
                likes=item.metadata.get("likes", 0),
                retweets=item.metadata.get("retweets", 0),
                replies=item.metadata.get("replies", 0),
                tweet_created_at=item.created_at,
                scraped_at=item.scraped_at,
                url=item.url,
                is_retweet=item.metadata.get("is_retweet", False),
                is_reply=item.metadata.get("is_reply", False),
            )
            
            db.add(tweet)
            tweets_stored += 1
            tweets_to_embed.append({
                "id": item.id,
                "content": item.content,
                "handle": handle,
                "url": item.url,
                "created_at": item.created_at.isoformat() + "Z",
            })
        
        await db.commit()
        
        # Invalidate tweets cache
        await cache.invalidate("tweets:*")
        
        # Store embeddings if requested
        embeddings_stored = 0
        if request.store_embeddings and tweets_to_embed:
            try:
                vector_store = get_vector_store()
                
                # Prepare documents
                docs = []
                texts = []
                for t in tweets_to_embed:
                    doc = {
                        "id": t["id"],
                        "content": t["content"],
                        "type": "tweet",
                        "source": f"@{t['handle']}",
                        "url": t["url"],
                        "created_at": t["created_at"],
                    }
                    docs.append(doc)
                    texts.append(t["content"])
                
                # Generate embeddings
                embeddings = await embedding_service.embed_batch(texts)
                
                # Store in vector database
                await vector_store.add_documents(
                    documents=docs,
                    embeddings=embeddings,
                    ids=[d["id"] for d in docs],
                )
                embeddings_stored = len(docs)
                
            except Exception as e:
                print(f"Warning: Failed to store embeddings: {e}")
        
        # Update tracked account if exists
        account_result = await db.execute(
            select(TrackedAccount).where(TrackedAccount.handle == handle)
        )
        account = account_result.scalar_one_or_none()
        if account:
            account.last_scraped_at = datetime.utcnow()
            if filtered_items:
                account.last_tweet_id = filtered_items[0].id
            await db.commit()
        
        return {
            "status": "success",
            "handle": handle,
            "tweets_scraped": len(filtered_items),
            "tweets_stored": tweets_stored,
            "embeddings_stored": embeddings_stored,
            "date_range": {
                "since": request.since.isoformat() if request.since else None,
                "until": request.until.isoformat() if request.until else None,
            },
            "tweets": [
                {
                    "id": item.id,
                    "content": item.content[:200] + "..." if len(item.content) > 200 else item.content,
                    "created_at": item.created_at.isoformat() + "Z",
                    "likes": item.metadata.get("likes", 0),
                    "retweets": item.metadata.get("retweets", 0),
                }
                for item in filtered_items[:10]  # Return first 10 for preview
            ],
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape/bulk")
async def scrape_all_tracked_accounts(
    db: AsyncSession = Depends(get_db),
    max_tweets_per_account: int = Query(20, ge=1, le=100),
    store_embeddings: bool = Query(True),
):
    """Scrape tweets from all active tracked accounts."""
    
    # Get all active accounts
    result = await db.execute(
        select(TrackedAccount).where(TrackedAccount.is_active == True)
    )
    accounts = result.scalars().all()
    
    if not accounts:
        return {"status": "success", "message": "No active accounts to scrape", "results": []}
    
    results = []
    for account in accounts:
        try:
            # Scrape tweets for this account
            request = ScrapeRequest(
                handle=account.handle,
                max_tweets=max_tweets_per_account,
                include_replies=account.scrape_replies,
                include_retweets=account.scrape_retweets,
                store_embeddings=store_embeddings,
            )
            
            scrape_result = await scrape_tweets(request, db)
            results.append({
                "handle": account.handle,
                "status": "success",
                "tweets_stored": scrape_result.get("tweets_stored", 0),
            })
            
        except Exception as e:
            results.append({
                "handle": account.handle,
                "status": "error",
                "error": str(e),
            })
    
    return {
        "status": "success",
        "accounts_processed": len(accounts),
        "results": results,
    }


# ============ Analytics Endpoints ============

@router.get("/analytics/sentiment")
async def get_sentiment_analytics(
    db: AsyncSession = Depends(get_db),
    time_range: str = Query("7d", description="Time range: 24h, 7d, 30d"),
):
    """Get sentiment data over time for charts."""
    
    # Parse time range and determine interval
    time_configs = {
        "24h": (timedelta(hours=24), timedelta(hours=2)),
        "7d": (timedelta(days=7), timedelta(hours=12)),
        "30d": (timedelta(days=30), timedelta(days=1)),
    }
    
    delta, interval = time_configs.get(time_range, time_configs["7d"])
    since_time = datetime.utcnow() - delta
    
    # Get all tweets in range with sentiment
    tweets_query = select(
        Tweet.tweet_created_at,
        Tweet.sentiment_label,
        Tweet.sentiment_score
    ).where(
        and_(
            Tweet.tweet_created_at >= since_time,
            Tweet.sentiment_label.isnot(None)
        )
    ).order_by(Tweet.tweet_created_at)
    
    result = await db.execute(tweets_query)
    tweets = result.all()
    
    # Group by time intervals
    timeline_data = []
    current_time = since_time
    end_time = datetime.utcnow()
    
    while current_time < end_time:
        interval_end = current_time + interval
        
        # Count sentiments in this interval
        interval_tweets = [t for t in tweets if current_time <= t[0] < interval_end]
        
        total = len(interval_tweets)
        if total > 0:
            bullish = sum(1 for t in interval_tweets if t[1] in ["positive", "bullish"])
            bearish = sum(1 for t in interval_tweets if t[1] in ["negative", "bearish"])
            neutral = sum(1 for t in interval_tweets if t[1] == "neutral")
            
            timeline_data.append({
                "timestamp": current_time.isoformat(),
                "bullish": round((bullish / total) * 100),
                "bearish": round((bearish / total) * 100),
                "neutral": round((neutral / total) * 100),
            })
        else:
            timeline_data.append({
                "timestamp": current_time.isoformat(),
                "bullish": 50,
                "bearish": 50,
                "neutral": 0,
            })
        
        current_time = interval_end
    
    return timeline_data


@router.get("/analytics/volume")
async def get_tweet_volume_analytics(
    db: AsyncSession = Depends(get_db),
    time_range: str = Query("7d", description="Time range: 24h, 7d, 30d"),
):
    """Get tweet volume by date for charts."""
    
    time_deltas = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    
    delta = time_deltas.get(time_range, timedelta(days=7))
    since_time = datetime.utcnow() - delta
    
    # Get tweets grouped by date
    tweets_query = select(
        func.date(Tweet.tweet_created_at).label("date"),
        func.count(Tweet.id).label("count")
    ).where(
        Tweet.tweet_created_at >= since_time
    ).group_by(
        func.date(Tweet.tweet_created_at)
    ).order_by(
        func.date(Tweet.tweet_created_at)
    )
    
    result = await db.execute(tweets_query)
    rows = result.all()
    
    return [
        {"date": str(row.date), "count": row.count}
        for row in rows
    ]


@router.get("/analytics/influencers")
async def get_top_influencers_analytics(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
):
    """Get top influencers by engagement."""
    
    # Get accounts with their total engagement
    influencers_query = select(
        Tweet.author_handle,
        Tweet.author_name,
        func.sum(Tweet.likes + Tweet.retweets + Tweet.replies).label("engagement"),
        func.count(Tweet.id).label("tweet_count")
    ).group_by(
        Tweet.author_handle, Tweet.author_name
    ).order_by(
        desc(func.sum(Tweet.likes + Tweet.retweets + Tweet.replies))
    ).limit(limit)
    
    result = await db.execute(influencers_query)
    rows = result.all()
    
    return [
        {
            "handle": row.author_handle,
            "name": row.author_name or row.author_handle,
            "engagement": int(row.engagement or 0),
            "tweet_count": row.tweet_count,
        }
        for row in rows
    ]


@router.get("/analytics/coins")
async def get_coin_mentions_analytics(
    db: AsyncSession = Depends(get_db),
    time_range: str = Query("7d", description="Time range: 24h, 7d, 30d"),
):
    """Get most mentioned coins from tweet content."""
    import re
    
    time_deltas = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    
    delta = time_deltas.get(time_range, timedelta(days=7))
    since_time = datetime.utcnow() - delta
    
    # Get all tweet content in time range
    tweets_query = select(Tweet.content).where(
        Tweet.tweet_created_at >= since_time
    )
    
    result = await db.execute(tweets_query)
    tweets = result.all()
    
    # Extract coin mentions ($BTC, $ETH, etc.)
    coin_pattern = r'\$([A-Z]{2,10})'
    coin_counts = {}
    
    for tweet in tweets:
        if tweet.content:
            matches = re.findall(coin_pattern, tweet.content.upper())
            for coin in matches:
                coin_counts[coin] = coin_counts.get(coin, 0) + 1
    
    # Sort by count and get top coins
    sorted_coins = sorted(coin_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    total_mentions = sum(count for _, count in sorted_coins) or 1
    
    return [
        {
            "coin": coin,
            "count": count,
            "percentage": round((count / total_mentions) * 100),
        }
        for coin, count in sorted_coins
    ]


@router.get("/analytics/heatmap")
async def get_activity_heatmap_analytics(
    db: AsyncSession = Depends(get_db),
):
    """Get tweet activity heatmap by day and hour - counts tweets per hour/day (no ML required)."""
    
    # Get all tweets from the last 4 weeks for better data coverage
    since_time = datetime.utcnow() - timedelta(days=28)
    
    tweets_query = select(Tweet.tweet_created_at).where(
        Tweet.tweet_created_at >= since_time
    )
    
    result = await db.execute(tweets_query)
    tweets = result.all()
    
    # Group by day of week (0-6) and hour (0-23)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    activity = {}
    
    for tweet in tweets:
        tweet_time = tweet[0]
        day_idx = tweet_time.weekday()
        hour = tweet_time.hour
        key = (day_idx, hour)
        activity[key] = activity.get(key, 0) + 1
    
    # Find max count for normalization
    max_count = max(activity.values()) if activity else 1
    
    # Generate data for all day/hour combinations (every 4 hours: 0, 4, 8, 12, 16, 20)
    heatmap_data = []
    for day_idx, day in enumerate(days):
        for hour in range(0, 24, 4):
            # Sum counts for the 4-hour block
            count = 0
            for h in range(hour, min(hour + 4, 24)):
                count += activity.get((day_idx, h), 0)
            
            # Normalize to 0-1 scale for intensity
            intensity = count / max_count if max_count > 0 else 0
            
            heatmap_data.append({
                "day": day,
                "hour": hour,
                "count": count,
                "intensity": round(intensity, 2),
            })
    
    return heatmap_data
