from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Optional
from datetime import datetime

from app.database.connection import get_db
from app.models.news import NewsArticle
from app.services.scrapers.news_scraper import NewsScraper
from app.services.ai.embeddings import embedding_service
from app.database.vector_store import get_vector_store
from app.services.cache import cache

router = APIRouter()

# Initialize scraper
news_scraper = NewsScraper()

# Cache TTLs
NEWS_CACHE_TTL = 300  # 5 minutes


@router.get("/")
async def get_news(
    db: AsyncSession = Depends(get_db),
    source: Optional[str] = Query(None, description="Filter by news source"),
    limit: int = Query(50, ge=1, le=100, description="Number of articles to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    category: Optional[str] = Query(None, description="Filter by category: market, regulation, defi, nft"),
    since: Optional[datetime] = Query(None, description="Filter news after this date"),
    until: Optional[datetime] = Query(None, description="Filter news before this date"),
):
    """Get scraped news articles from database with optional filtering."""
    
    # Check cache first
    cache_key = f"news:list:{source}:{limit}:{offset}:{category}:{since}:{until}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    # Build query
    query = select(NewsArticle).order_by(desc(NewsArticle.published_at))
    count_query = select(func.count(NewsArticle.id))
    
    # Apply filters
    filters = []
    if source:
        filters.append(NewsArticle.source_id == source)
    if category:
        filters.append(NewsArticle.category == category)
    if since:
        filters.append(NewsArticle.published_at >= since)
    if until:
        filters.append(NewsArticle.published_at <= until)
    
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
    articles = result.scalars().all()
    
    response = {
        "articles": [article.to_dict() for article in articles],
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "source": source,
            "category": category,
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
        }
    }
    
    # Cache the response
    await cache.set(cache_key, response, ttl=NEWS_CACHE_TTL)
    
    return response


@router.get("/sources")
async def get_news_sources():
    """Get list of news sources being tracked."""
    sources = [
        {
            "id": source_id, 
            "name": config["name"], 
            "url": config["url"],
            "rss": config["rss"],
            "active": True
        }
        for source_id, config in NewsScraper.NEWS_SOURCES.items()
    ]
    return {
        "sources": sources,
        "total": len(sources),
    }


@router.post("/sources")
async def add_news_source(name: str, url: str, rss_feed: Optional[str] = None):
    """Add a new news source to track."""
    # TODO: Validate and add to database
    return {
        "message": f"News source '{name}' added",
        "name": name,
        "url": url,
        "rss_feed": rss_feed,
    }


@router.get("/{article_id}")
async def get_article_by_id(article_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific news article by ID with full details."""
    # Try to find by ID or URL hash
    result = await db.execute(
        select(NewsArticle).where(NewsArticle.id == article_id)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail=f"Article not found: {article_id}")
    
    return article.to_dict()


@router.get("/trending/topics")
async def get_trending_topics(hours: int = Query(24, ge=1, le=168)):
    """Get trending topics from news in the last N hours."""
    # TODO: Analyze recent news
    return {
        "trending": [
            {"topic": "Bitcoin ETF", "mentions": 45, "sentiment": "positive"},
            {"topic": "SEC Regulation", "mentions": 32, "sentiment": "negative"},
            {"topic": "Ethereum Upgrade", "mentions": 28, "sentiment": "positive"},
        ],
        "period_hours": hours,
    }


@router.post("/scrape")
async def scrape_news(
    db: AsyncSession = Depends(get_db),
    source: Optional[str] = Query(None, description="Specific source to scrape (e.g., 'coindesk'). If not provided, scrapes all sources."),
    max_articles: int = Query(10, ge=1, le=50, description="Maximum articles per source"),
    store_embeddings: bool = Query(True, description="Whether to generate and store embeddings for RAG"),
):
    """
    Scrape news from RSS feeds, store in PostgreSQL, and optionally store in vector database.
    
    This fetches real news articles from crypto news sources.
    """
    try:
        all_articles = []
        new_articles_count = 0
        
        # Determine which sources to scrape
        if source:
            sources_to_scrape = [source] if source in NewsScraper.NEWS_SOURCES else []
            if not sources_to_scrape:
                raise HTTPException(status_code=400, detail=f"Unknown source: {source}. Available: {list(NewsScraper.NEWS_SOURCES.keys())}")
        else:
            sources_to_scrape = list(NewsScraper.NEWS_SOURCES.keys())
        
        # Scrape each source
        for src in sources_to_scrape:
            items = await news_scraper.scrape(target=src, max_articles=max_articles)
            for item in items:
                # Check if article already exists (by URL or ID)
                existing = await db.execute(
                    select(NewsArticle).where(NewsArticle.url == item.url)
                )
                if existing.scalar_one_or_none():
                    continue  # Skip duplicates
                
                # Create new article record
                article_record = NewsArticle(
                    id=item.id,
                    title=item.metadata.get("title", ""),
                    content=item.content,
                    source_id=item.metadata.get("source_id", src),
                    source_name=item.metadata.get("source_name", src),
                    url=item.url,
                    author=item.metadata.get("author"),
                    image_url=item.metadata.get("image_url"),
                    published_at=item.created_at,
                    scraped_at=item.scraped_at,
                    category=item.metadata.get("category"),
                    tags=item.metadata.get("tags", []),
                )
                
                db.add(article_record)
                new_articles_count += 1
                
                article = {
                    "id": item.id,
                    "title": item.metadata.get("title", ""),
                    "content": item.content[:500] + "..." if len(item.content) > 500 else item.content,
                    "full_content": item.content,
                    "source_id": item.metadata.get("source_id", src),
                    "source_name": item.metadata.get("source_name", src),
                    "url": item.url,
                    "author": item.metadata.get("author", ""),
                    "image_url": item.metadata.get("image_url"),
                    "published_at": item.created_at.isoformat() + "Z",
                    "scraped_at": item.scraped_at.isoformat() + "Z",
                    "tags": item.metadata.get("tags", []),
                }
                all_articles.append(article)
        
        # Commit to database
        await db.commit()
        
        # Invalidate news cache so fresh data is served
        await cache.invalidate("news:*")
        
        # Store embeddings if requested
        embeddings_stored = 0
        embedding_error = None
        if store_embeddings and all_articles:
            try:
                vector_store = get_vector_store()
                
                # Prepare documents for embedding
                docs = []
                texts = []
                for article in all_articles:
                    doc = {
                        "id": article["id"],
                        "content": f"{article['title']}\n\n{article['full_content']}",
                        "type": "news",
                        "source": article["source_name"],
                        "url": article["url"],
                        "title": article["title"],
                        "published_at": article["published_at"],
                    }
                    docs.append(doc)
                    texts.append(doc["content"])
                
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
                # Log the error - include it in response for debugging
                import traceback
                print(f"Warning: Failed to store embeddings: {e}")
                traceback.print_exc()
                embedding_error = str(e)
        
        return {
            "status": "success",
            "articles_scraped": len(all_articles),
            "new_articles_saved": new_articles_count,
            "sources_scraped": sources_to_scrape,
            "embedding_error": embedding_error,
            "embeddings_stored": embeddings_stored,
            "articles": all_articles,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
