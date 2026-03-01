from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.api.routes import tweets, news, search, chat, prices
from app.database.connection import init_db, close_db
from app.services.scheduler import scraper_scheduler
from app.services.cache import cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()
    print("✅ Database connected")
    
    # Connect Redis cache
    await cache.connect()
    
    # Start the scheduler for auto-scraping
    scraper_scheduler.start()
    print("⏰ Scheduler started - auto-scraping enabled")
    
    yield
    
    # Shutdown
    scraper_scheduler.stop()
    await cache.disconnect()
    await close_db()
    print("👋 Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Crypto news and sentiment aggregator powered by AI",
    lifespan=lifespan,
)

# CORS Middleware - must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(tweets.router, prefix="/api/tweets", tags=["Tweets"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(prices.router, prefix="/api/prices", tags=["Prices"])


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    redis_health = await cache.health_check()
    return {
        "status": "healthy",
        "database": "connected",
        "redis": redis_health,
        "vector_store": "ready",
    }


@app.get("/api/scheduler/status", tags=["Scheduler"])
async def get_scheduler_status():
    """Get scheduler status and job info."""
    return scraper_scheduler.get_job_status()


@app.post("/api/scheduler/scrape", tags=["Scheduler"])
async def trigger_manual_scrape(target_type: str = "all"):
    """
    Manually trigger a scrape.
    
    Args:
        target_type: 'twitter', 'news', or 'all'
    """
    results = {}
    
    if target_type in ["twitter", "all"]:
        twitter_result = await scraper_scheduler.trigger_scrape("twitter")
        results["twitter"] = twitter_result
    
    if target_type in ["news", "all"]:
        news_result = await scraper_scheduler.trigger_scrape("news")
        results["news"] = news_result
    
    return {"status": "scrape_triggered", "results": results}
