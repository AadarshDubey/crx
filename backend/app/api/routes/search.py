from fastapi import APIRouter, Query, Depends
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.sql import func

from app.database.connection import get_db
from app.models.tweet import Tweet

router = APIRouter()


class SearchQuery(BaseModel):
    """Search query model."""
    query: str
    filters: Optional[dict] = None
    limit: int = 20
    use_semantic: bool = True


@router.get("/")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    type: Optional[str] = Query(None, description="Content type: tweets, news, all"),
    limit: int = Query(20, ge=1, le=100),
    semantic: bool = Query(False, description="Use semantic search (AI-powered)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Search across tweets by content, author handle, or author name.
    
    Supports case-insensitive keyword search.
    """
    # Build search query - search in content, author_handle, and author_name
    search_term = f"%{q}%"
    
    query = select(Tweet).where(
        or_(
            Tweet.content.ilike(search_term),
            Tweet.author_handle.ilike(search_term),
            Tweet.author_name.ilike(search_term),
        )
    ).order_by(desc(Tweet.tweet_created_at)).limit(limit)
    
    result = await db.execute(query)
    tweets = result.scalars().all()
    
    # Return tweets as list (frontend expects Tweet[] format)
    return [tweet.to_dict() for tweet in tweets]


@router.post("/semantic")
async def semantic_search(search: SearchQuery, db: AsyncSession = Depends(get_db)):
    """
    Perform semantic search using vector embeddings.
    
    This searches for conceptually similar content, not just keyword matches.
    Falls back to keyword search if vector store is not available.
    """
    # Fallback to keyword search
    search_term = f"%{search.query}%"
    
    query = select(Tweet).where(
        or_(
            Tweet.content.ilike(search_term),
            Tweet.author_handle.ilike(search_term),
            Tweet.author_name.ilike(search_term),
        )
    ).order_by(desc(Tweet.tweet_created_at)).limit(search.limit)
    
    result = await db.execute(query)
    tweets = result.scalars().all()
    
    return {
        "query": search.query,
        "results": [tweet.to_dict() for tweet in tweets],
        "total": len(tweets),
        "search_type": "keyword",  # TODO: Implement actual semantic search
    }


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Get search suggestions based on partial query."""
    search_term = f"%{q}%"
    
    # Get unique author handles and names that match
    handles_query = select(Tweet.author_handle).where(
        Tweet.author_handle.ilike(search_term)
    ).distinct().limit(limit)
    
    names_query = select(Tweet.author_name).where(
        Tweet.author_name.ilike(search_term)
    ).distinct().limit(limit)
    
    handles_result = await db.execute(handles_query)
    names_result = await db.execute(names_query)
    
    handles = [f"@{h[0]}" for h in handles_result.all() if h[0]]
    names = [n[0] for n in names_result.all() if n[0]]
    
    # Combine and dedupe
    suggestions = list(dict.fromkeys(handles + names))[:limit]
    
    return {"suggestions": suggestions}


@router.get("/filters")
async def get_available_filters(db: AsyncSession = Depends(get_db)):
    """Get available filter options for search."""
    # Get unique accounts from database
    accounts_query = select(Tweet.author_handle).distinct().limit(50)
    accounts_result = await db.execute(accounts_query)
    accounts = [a[0] for a in accounts_result.all() if a[0]]
    
    return {
        "content_types": ["tweets", "news", "all"],
        "sentiments": ["positive", "negative", "neutral"],
        "date_ranges": ["today", "week", "month", "all"],
        "accounts": accounts,
        "sources": [],
        "topics": [
            "bitcoin", "ethereum", "defi", "nft", 
            "regulation", "market", "altcoins"
        ],
    }

