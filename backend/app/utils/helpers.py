import re
from datetime import datetime, timedelta
from typing import Optional, List
import hashlib


def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    # Remove URLs
    text = re.sub(r'http\S+|www\.\S+', '', text)
    # Remove excessive whitespace
    text = " ".join(text.split())
    return text.strip()


def extract_tickers(text: str) -> List[str]:
    """Extract cryptocurrency tickers from text (e.g., $BTC, $ETH)."""
    pattern = r'\$([A-Z]{2,10})'
    matches = re.findall(pattern, text.upper())
    return list(set(matches))


def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text."""
    pattern = r'#(\w+)'
    matches = re.findall(pattern, text)
    return list(set(matches))


def generate_id(*args) -> str:
    """Generate a deterministic ID from components."""
    combined = "_".join(str(arg) for arg in args)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def parse_relative_time(time_str: str) -> Optional[datetime]:
    """
    Parse relative time strings like '2h', '3d', '1w'.
    
    Returns datetime offset from now.
    """
    if not time_str:
        return None
    
    time_str = time_str.lower().strip()
    now = datetime.utcnow()
    
    patterns = [
        (r'(\d+)\s*s(ec)?', timedelta(seconds=1)),
        (r'(\d+)\s*m(in)?', timedelta(minutes=1)),
        (r'(\d+)\s*h(our)?', timedelta(hours=1)),
        (r'(\d+)\s*d(ay)?', timedelta(days=1)),
        (r'(\d+)\s*w(eek)?', timedelta(weeks=1)),
        (r'(\d+)\s*mo(nth)?', timedelta(days=30)),
    ]
    
    for pattern, unit in patterns:
        match = re.match(pattern, time_str)
        if match:
            value = int(match.group(1))
            return now - (unit * value)
    
    return None


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length, preserving word boundaries."""
    if len(text) <= max_length:
        return text
    
    truncated = text[:max_length - len(suffix)]
    # Try to break at word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.7:
        truncated = truncated[:last_space]
    
    return truncated + suffix


def format_number(num: int) -> str:
    """Format large numbers with K, M suffixes."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def is_valid_twitter_handle(handle: str) -> bool:
    """Validate Twitter handle format."""
    handle = handle.lstrip("@")
    if not handle:
        return False
    # Twitter handles: 1-15 chars, alphanumeric and underscores
    return bool(re.match(r'^[A-Za-z0-9_]{1,15}$', handle))


def is_valid_url(url: str) -> bool:
    """Basic URL validation."""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url, re.IGNORECASE))


# Common crypto-related keywords for categorization
CRYPTO_KEYWORDS = {
    "bullish": ["bullish", "moon", "pump", "buy", "long", "breakout", "ath", "gains"],
    "bearish": ["bearish", "crash", "dump", "sell", "short", "correction", "fear"],
    "defi": ["defi", "yield", "liquidity", "swap", "farm", "stake", "lending"],
    "nft": ["nft", "mint", "collection", "pfp", "opensea", "blur"],
    "regulation": ["sec", "regulation", "lawsuit", "ban", "legal", "compliance"],
    "technical": ["support", "resistance", "rsi", "macd", "chart", "pattern"],
}


def categorize_content(text: str) -> List[str]:
    """Categorize content based on keywords."""
    text_lower = text.lower()
    categories = []
    
    for category, keywords in CRYPTO_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            categories.append(category)
    
    return categories if categories else ["general"]
