from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App Config
    APP_NAME: str = "Crypto Pulse"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/crypto_pulse"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Twitter/X API (optional - can use scraping fallback)
    TWITTER_BEARER_TOKEN: Optional[str] = None
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # Groq (Free alternative to OpenAI)
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # LLM Provider: "openai" or "groq"
    LLM_PROVIDER: str = "groq"
    
    # RapidAPI (for Twitter scraping)
    RAPIDAPI_KEY: Optional[str] = None
    
    # Vector Database
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "crypto-pulse"
    USE_CHROMA: bool = True  # Use ChromaDB locally if True, Pinecone if False
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    # Scraping Config
    SCRAPE_INTERVAL_MINUTES: int = 15
    MAX_TWEETS_PER_ACCOUNT: int = 50
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
