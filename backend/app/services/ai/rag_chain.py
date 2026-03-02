from typing import List, Optional, AsyncGenerator
from openai import AsyncOpenAI
from groq import AsyncGroq
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import re

from app.config import settings
from app.services.ai.embeddings import embedding_service
from app.database.vector_store import get_vector_store


class Source(BaseModel):
    """Source document used in RAG response."""
    id: str
    content: str
    source_type: str  # tweet, news
    url: Optional[str]
    relevance_score: float


class RAGResponse(BaseModel):
    """Response from RAG chain."""
    answer: str
    sources: List[Source]
    tokens_used: int


class RAGChain:
    """
    Retrieval-Augmented Generation chain for crypto Q&A.
    
    Combines vector search with LLM to answer questions
    based on scraped tweets and news.
    Supports both OpenAI and Groq as LLM providers.
    Includes agent capabilities for price queries.
    """
    
    # Price-related keywords for detection
    PRICE_KEYWORDS = [
        "price", "cost", "worth", "value", "trading at",
        "change", "changed", "movement", "moved", "up", "down",
        "percent", "%", "gain", "loss", "increase", "decrease",
        "ath", "all time high", "all-time high", "atl", "all time low",
        "market cap", "marketcap", "volume", "24h", "7d", "30d",
        "last week", "last month", "past week", "past month", "yesterday",
        "compare", "comparison", "performance", "roi", "return",
        "bought", "buy", "sell", "sold", "investment",
    ]
    
    # Coin patterns
    COIN_PATTERNS = [
        r'\b(btc|bitcoin)\b',
        r'\b(eth|ethereum|ether)\b',
        r'\b(sol|solana)\b',
        r'\b(xrp|ripple)\b',
        r'\b(ada|cardano)\b',
        r'\b(doge|dogecoin)\b',
        r'\b(bnb|binance)\b',
        r'\b(dot|polkadot)\b',
        r'\b(matic|polygon)\b',
        r'\b(link|chainlink)\b',
        r'\b(avax|avalanche)\b',
        r'\b(uni|uniswap)\b',
        r'\b(atom|cosmos)\b',
        r'\b(ltc|litecoin)\b',
        r'\b(shib|shiba)\b',
        r'\b(pepe)\b',
        r'\b(arb|arbitrum)\b',
        r'\b(op|optimism)\b',
    ]
    
    # Cache for tracked accounts (refreshed periodically)
    _tracked_accounts_cache: List[dict] = []
    _cache_timestamp: datetime = None
    _cache_ttl_seconds: int = 300  # 5 minutes cache
    
    SYSTEM_PROMPT = """You are an expert crypto market analyst with access to real-time tweets, news articles, and price data from key figures in the cryptocurrency space.

Your capabilities:
- Analyze sentiment and tone from tweets and news
- Identify market-moving statements and their potential impact
- Provide nuanced interpretation of what influential people are saying
- Connect statements to broader market context

Guidelines:
- When analyzing a specific person's content, focus on THEIR actual words and statements
- Identify the overall sentiment (bullish/bearish/neutral) with specific evidence
- Highlight key themes and topics they're discussing
- Note any market predictions or hints they're making
- Assess potential market impact based on their influence
- Be specific - quote or paraphrase their actual statements
- If context is limited, acknowledge what you have and what's missing"""

    RAG_PROMPT = """Based on the following content, provide a sophisticated analysis for the user's question.

{person_context}Context (tweets and news):
{context}

{price_context}

User Question: {question}

Provide a thoughtful, well-structured response that:
1. Directly addresses what was asked
2. References specific content from the sources when relevant
3. Analyzes sentiment and potential market implications
4. Is clear and professional in tone

If analyzing a specific person's tweets, structure your response as:
- **Overall Sentiment**: [bullish/bearish/neutral with brief explanation]
- **Key Themes**: What they're talking about
- **Notable Statements**: Specific quotes or paraphrases
- **Market Impact**: Potential implications for the market"""

    PERSON_CONTEXT_TEMPLATE = """You are analyzing content from @{handle}{name_part}.
Focus on their direct statements and what they reveal about their views on the market.

"""

    def __init__(self):
        # Choose LLM provider based on settings
        self.provider = settings.LLM_PROVIDER.lower()
        
        if self.provider == "groq" and settings.GROQ_API_KEY:
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            self.model = settings.GROQ_MODEL
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
            self.provider = "openai"
        
        self.vector_store = get_vector_store()
        self.top_k = 10  # Increased for better coverage when filtering by source
        
        # Lazy load price service
        self._price_service = None
    
    @property
    def price_service(self):
        """Lazy load CoinGecko service."""
        if self._price_service is None:
            from app.services.prices.coingecko import coingecko_service
            self._price_service = coingecko_service
        return self._price_service
    
    async def _get_tracked_accounts(self) -> List[dict]:
        """
        Get tracked accounts from database with caching.
        Returns list of dicts with 'handle' and 'name' keys.
        """
        now = datetime.utcnow()
        
        # Check if cache is valid
        if (RAGChain._cache_timestamp and 
            RAGChain._tracked_accounts_cache and
            (now - RAGChain._cache_timestamp).total_seconds() < RAGChain._cache_ttl_seconds):
            return RAGChain._tracked_accounts_cache
        
        # Refresh cache from database
        try:
            from app.database.connection import async_session
            from app.models.account import TrackedAccount
            from sqlalchemy import select
            
            async with async_session() as session:
                result = await session.execute(
                    select(TrackedAccount.handle, TrackedAccount.name).where(TrackedAccount.is_active == True)
                )
                accounts = [{"handle": row[0], "name": row[1]} for row in result.all()]
                
            RAGChain._tracked_accounts_cache = accounts
            RAGChain._cache_timestamp = now
            return accounts
            
        except Exception as e:
            print(f"Warning: Could not fetch tracked accounts: {e}")
            return RAGChain._tracked_accounts_cache or []
    
    def _get_sources_from_vectordb(self) -> List[str]:
        """Get unique sources from the vector database."""
        try:
            # Get all unique sources from ChromaDB
            collection = self.vector_store.collection
            results = collection.get(include=["metadatas"])
            
            sources = set()
            for meta in results.get("metadatas", []):
                if meta and "source" in meta:
                    sources.add(meta["source"])
            
            return list(sources)
        except Exception as e:
            print(f"Warning: Could not fetch sources from vector DB: {e}")
            return []
    
    async def _extract_mentioned_accounts(self, question: str) -> List[dict]:
        """
        Extract Twitter account handles mentioned in the question.
        Returns list of dicts with 'handle' and 'name' for context.
        
        ONLY triggers for tweet/post related queries, NOT for price queries.
        
        Matches against:
        1. Direct @handle mentions (e.g., @cz_binance) - INCLUDING NEW/UNTRACKED ACCOUNTS
        2. Handle names without @ (e.g., cz_binance, watcherguru)
        3. Person names from tracked accounts (e.g., "CZ", "Saylor")
        4. Common aliases and variations
        """
        question_lower = question.lower()
        matched_accounts = []
        
        # FIRST: Check if this is a tweet-related query
        # Only scrape Twitter if user is explicitly asking about tweets/posts
        tweet_keywords = [
            'tweet', 'tweets', 'tweeted', 'tweeting',
            'post', 'posts', 'posted', 'posting',
            'said', 'saying', 'says',
            'mentioned', 'mention',
            'account', 'profile',
            'influencer', 'influencers',
            'twitter', 'x.com',
            'sentiment', 'analysis',
            'summary', 'summarize',
            'latest from', 'recent from',
        ]
        
        # Check if question is about tweets/influencers
        is_tweet_query = any(kw in question_lower for kw in tweet_keywords)
        
        # Also check for explicit @mentions (always indicate Twitter intent)
        has_at_mention = '@' in question
        
        # If not a tweet-related query and no @mention, skip account detection
        if not is_tweet_query and not has_at_mention:
            return []
        
        # Pattern 1: Direct @handle mentions - extract ALL handles including new ones
        handle_pattern = r'@(\w+)'
        direct_handles = re.findall(handle_pattern, question)  # Use original case
        
        # Also try to detect handles mentioned without @ that look like Twitter handles
        # Look for phrases like "from X", "by X", "tweets from X", etc.
        # Only use these patterns for tweet-related queries
        handle_context_patterns = [
            r'(?:tweets?|posts?)\s+(?:from|by|of)\s+([A-Za-z0-9_]{3,20})\b',
            r"([A-Za-z0-9_]{3,20})(?:'s?\s+(?:tweets?|posts?|account))",
            r'(?:from|by)\s+([A-Za-z0-9_]{3,20})\s+(?:on\s+)?(?:twitter|x\.com)',
        ]
        
        potential_handles = set()
        for pattern in handle_context_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            for match in matches:
                # Filter out common words and crypto names
                excluded_words = {
                    'the', 'this', 'that', 'what', 'about', 'latest', 'recent', 'new', 'old', 
                    'all', 'any', 'some', 'their', 'account', 'tweets', 'tweet', 'posts', 'post',
                    # Crypto names that should NOT be treated as handles
                    'bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol', 'dogecoin', 'doge',
                    'cardano', 'ada', 'ripple', 'xrp', 'polkadot', 'dot', 'avalanche', 'avax',
                    'chainlink', 'link', 'polygon', 'matic', 'litecoin', 'ltc', 'uniswap', 'uni',
                    'crypto', 'coin', 'token', 'price', 'market', 'trading', 'buy', 'sell',
                }
                if match.lower() not in excluded_words and len(match) >= 3:
                    potential_handles.add(match)
        
        # Get tracked accounts and vector DB sources
        tracked_accounts = await self._get_tracked_accounts()
        vectordb_sources = self._get_sources_from_vectordb()
        
        # Build a comprehensive lookup of all known handles
        all_handles = {}  # lowercase_handle -> {"handle": original, "name": name}
        
        # From tracked accounts
        for acc in tracked_accounts:
            handle_lower = acc["handle"].lower()
            all_handles[handle_lower] = {"handle": f"@{acc['handle']}", "name": acc.get("name")}
        
        # From vector DB sources (handles start with @)
        for source in vectordb_sources:
            if source.startswith("@"):
                handle_lower = source[1:].lower()
                if handle_lower not in all_handles:
                    all_handles[handle_lower] = {"handle": source, "name": None}
        
        # Check direct @mentions - add ALL mentioned handles, even if not tracked
        for handle in direct_handles:
            handle_lower = handle.lower()
            if handle_lower in all_handles:
                if all_handles[handle_lower] not in matched_accounts:
                    matched_accounts.append(all_handles[handle_lower])
            else:
                # NEW: Add untracked accounts too!
                new_account = {"handle": f"@{handle}", "name": None}
                if new_account not in matched_accounts:
                    matched_accounts.append(new_account)
        
        # Check potential handles from context patterns
        for handle in potential_handles:
            handle_lower = handle.lower()
            if handle_lower in all_handles:
                if all_handles[handle_lower] not in matched_accounts:
                    matched_accounts.append(all_handles[handle_lower])
            else:
                # Check if it looks like a valid Twitter handle (alphanumeric + underscore)
                if re.match(r'^[A-Za-z0-9_]+$', handle) and len(handle) >= 3:
                    new_account = {"handle": f"@{handle}", "name": None}
                    if new_account not in matched_accounts:
                        matched_accounts.append(new_account)
        
        # Check for handle names in text (without @) - only for known handles
        for handle_lower, account_info in all_handles.items():
            # Match the handle itself
            if re.search(rf'\b{re.escape(handle_lower)}\b', question_lower):
                if account_info not in matched_accounts:
                    matched_accounts.append(account_info)
            
            # Also match name if available
            if account_info.get("name"):
                name_lower = account_info["name"].lower()
                # Match full name or first/last name parts
                name_parts = name_lower.split()
                for part in name_parts:
                    if len(part) > 2 and re.search(rf'\b{re.escape(part)}\b', question_lower):
                        if account_info not in matched_accounts:
                            matched_accounts.append(account_info)
                            break
        
        # Common alias mappings (for popular figures)
        common_aliases = {
            "cz": "cz_binance",
            "changpeng": "cz_binance", 
            "saylor": "saylor",
            "michael saylor": "saylor",
            "vitalik": "vitalikbuterin",
            "elon": "elonmusk",
            "musk": "elonmusk",
        }
        
        for alias, handle in common_aliases.items():
            if re.search(rf'\b{re.escape(alias)}\b', question_lower):
                handle_lower = handle.lower()
                if handle_lower in all_handles:
                    if all_handles[handle_lower] not in matched_accounts:
                        matched_accounts.append(all_handles[handle_lower])
                else:
                    # Add even if not tracked
                    new_account = {"handle": f"@{handle}", "name": None}
                    if new_account not in matched_accounts:
                        matched_accounts.append(new_account)
        
        return matched_accounts
    
    def _detect_price_query(self, question: str) -> bool:
        """Detect if the question is asking about prices."""
        question_lower = question.lower()
        
        # Check for price keywords
        has_price_keyword = any(kw in question_lower for kw in self.PRICE_KEYWORDS)
        
        # Check for coin mentions
        has_coin = any(re.search(pattern, question_lower) for pattern in self.COIN_PATTERNS)
        
        return has_price_keyword and has_coin
    
    def _extract_coins(self, question: str) -> List[str]:
        """Extract coin names/symbols from question."""
        question_lower = question.lower()
        coins = []
        
        # Mapping from pattern to CoinGecko ID
        coin_mapping = {
            'btc': 'bitcoin', 'bitcoin': 'bitcoin',
            'eth': 'ethereum', 'ethereum': 'ethereum', 'ether': 'ethereum',
            'sol': 'solana', 'solana': 'solana',
            'xrp': 'ripple', 'ripple': 'ripple',
            'ada': 'cardano', 'cardano': 'cardano',
            'doge': 'dogecoin', 'dogecoin': 'dogecoin',
            'bnb': 'binancecoin', 'binance': 'binancecoin',
            'dot': 'polkadot', 'polkadot': 'polkadot',
            'matic': 'matic-network', 'polygon': 'matic-network',
            'link': 'chainlink', 'chainlink': 'chainlink',
            'avax': 'avalanche-2', 'avalanche': 'avalanche-2',
            'uni': 'uniswap', 'uniswap': 'uniswap',
            'atom': 'cosmos', 'cosmos': 'cosmos',
            'ltc': 'litecoin', 'litecoin': 'litecoin',
            'shib': 'shiba-inu', 'shiba': 'shiba-inu',
            'pepe': 'pepe',
            'arb': 'arbitrum', 'arbitrum': 'arbitrum',
            'op': 'optimism', 'optimism': 'optimism',
        }
        
        for word in re.findall(r'\b\w+\b', question_lower):
            if word in coin_mapping and coin_mapping[word] not in coins:
                coins.append(coin_mapping[word])
        
        return coins if coins else ['bitcoin']  # Default to bitcoin
    
    def _extract_time_range(self, question: str) -> tuple:
        """Extract time range from question. Returns (from_date, to_date, days)."""
        question_lower = question.lower()
        now = datetime.utcnow()
        
        # Check for common time patterns
        if 'yesterday' in question_lower:
            return now - timedelta(days=1), now, 1
        elif '24h' in question_lower or '24 hour' in question_lower:
            return now - timedelta(days=1), now, 1
        elif 'week' in question_lower or '7d' in question_lower or '7 day' in question_lower:
            return now - timedelta(days=7), now, 7
        elif 'month' in question_lower or '30d' in question_lower or '30 day' in question_lower:
            return now - timedelta(days=30), now, 30
        elif '3 month' in question_lower or '90d' in question_lower:
            return now - timedelta(days=90), now, 90
        elif 'year' in question_lower or '365d' in question_lower:
            return now - timedelta(days=365), now, 365
        else:
            # Default to 7 days
            return now - timedelta(days=7), now, 7
    
    async def _get_price_context(self, coins: List[str], from_date: datetime, to_date: datetime, days: int) -> str:
        """Fetch price data and format as context for LLM."""
        try:
            price_data = []
            
            for coin in coins[:3]:  # Limit to 3 coins to avoid API overload
                try:
                    # Get current price
                    current = await self.price_service.get_current_price([coin], include_24h_change=True)
                    
                    if coin in current:
                        coin_data = current[coin]
                        current_price = coin_data.get('usd', 0)
                        change_24h = coin_data.get('usd_24h_change', 0)
                        market_cap = coin_data.get('usd_market_cap', 0)
                        
                        # Get historical range for percentage calculation
                        historical = await self.price_service.get_price_range(
                            coin=coin,
                            from_date=from_date,
                            to_date=to_date,
                            vs_currency='usd'
                        )
                        
                        prices = historical.get('prices', [])
                        if prices:
                            start_price = prices[0]['price']
                            end_price = prices[-1]['price']
                            period_change = ((end_price - start_price) / start_price) * 100 if start_price else 0
                            
                            # Calculate high/low in period
                            price_values = [p['price'] for p in prices]
                            period_high = max(price_values)
                            period_low = min(price_values)
                            
                            price_data.append(
                                f"**{coin.upper()}**:\n"
                                f"  - Current Price: ${current_price:,.2f}\n"
                                f"  - 24h Change: {change_24h:+.2f}%\n"
                                f"  - {days}-day Change: {period_change:+.2f}%\n"
                                f"  - {days}-day High: ${period_high:,.2f}\n"
                                f"  - {days}-day Low: ${period_low:,.2f}\n"
                                f"  - Market Cap: ${market_cap:,.0f}"
                            )
                        else:
                            price_data.append(
                                f"**{coin.upper()}**: Current Price: ${current_price:,.2f}, 24h Change: {change_24h:+.2f}%"
                            )
                            
                except Exception as e:
                    price_data.append(f"**{coin.upper()}**: Price data unavailable ({str(e)})")
            
            if price_data:
                return "Real-time Price Data:\n" + "\n\n".join(price_data)
            return ""
            
        except Exception as e:
            return f"Price data fetch error: {str(e)}"
    
    async def query(
        self, 
        question: str,
        conversation_history: Optional[List[dict]] = None,
        filter_type: Optional[str] = None,  # "tweets", "news", or None for all
    ) -> RAGResponse:
        """
        Answer a question using RAG.
        
        Args:
            question: User's question
            conversation_history: Previous messages for context
            filter_type: Filter to specific content type
            
        Returns:
            RAGResponse with answer and sources
        """
        # Step 1: Embed the question
        query_embedding = await embedding_service.embed_for_search(question)
        
        # Step 1.5: Check if specific accounts are mentioned (async)
        mentioned_accounts = await self._extract_mentioned_accounts(question)
        
        # Step 2: Retrieve relevant documents
        # If specific accounts are mentioned, do two searches:
        # 1. Filtered search for content from those accounts
        # 2. General search for other relevant context
        documents = []
        person_context = ""
        
        if mentioned_accounts:
            # Build person context for the prompt
            handles = [acc["handle"] for acc in mentioned_accounts]
            names = [acc.get("name") or acc["handle"].lstrip("@") for acc in mentioned_accounts]
            
            if len(mentioned_accounts) == 1:
                acc = mentioned_accounts[0]
                name_part = f" ({acc['name']})" if acc.get("name") else ""
                person_context = self.PERSON_CONTEXT_TEMPLATE.format(
                    handle=acc["handle"].lstrip("@"),
                    name_part=name_part
                )
            else:
                person_context = f"You are analyzing content from multiple accounts: {', '.join(handles)}.\n\n"
            
            # First, get documents from mentioned accounts
            for account in mentioned_accounts:
                account_docs = await self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=self.top_k,
                    filter_metadata={"source": account["handle"]},
                )
                documents.extend(account_docs)
            
            # Then get general context (limited to avoid overwhelming)
            general_docs = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=5,
                filter_metadata={"type": filter_type} if filter_type else None,
            )
            # Add general docs that aren't duplicates
            existing_ids = {d["id"] for d in documents}
            for doc in general_docs:
                if doc["id"] not in existing_ids:
                    documents.append(doc)
        else:
            # Standard search without account filtering
            filter_metadata = None
            if filter_type:
                filter_metadata = {"type": filter_type}
            
            documents = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=self.top_k,
                filter_metadata=filter_metadata,
            )
        
        # Step 3: Format context
        context = self._format_context(documents)
        
        # Step 3.5: Check if this is a price query and fetch price data
        price_context = ""
        if self._detect_price_query(question):
            coins = self._extract_coins(question)
            from_date, to_date, days = self._extract_time_range(question)
            price_context = await self._get_price_context(coins, from_date, to_date, days)
        
        # Step 4: Build messages
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-6:]:  # Keep last 6 messages
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
        
        # Add current question with context (including person context if applicable)
        messages.append({
            "role": "user",
            "content": self.RAG_PROMPT.format(
                person_context=person_context,
                context=context, 
                price_context=price_context, 
                question=question
            )
        })
        
        # Step 5: Generate response
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,  # Increased for more detailed responses
            )
            
            answer = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
        except Exception as e:
            answer = f"I encountered an error processing your question: {str(e)}"
            tokens_used = 0
        
        # Format sources
        sources = [
            Source(
                id=doc["id"],
                content=doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                source_type=doc.get("metadata", {}).get("type", "unknown"),
                url=doc.get("metadata", {}).get("url"),
                relevance_score=1 - doc.get("distance", 0),  # Convert distance to similarity
            )
            for doc in documents
        ]
        
        return RAGResponse(
            answer=answer,
            sources=sources,
            tokens_used=tokens_used,
        )
    
    async def stream_query(
        self, 
        question: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream RAG response for better UX.
        
        Yields chunks of the response as they're generated.
        """
        # Get query embedding and documents
        query_embedding = await embedding_service.embed_for_search(question)
        
        # Check for mentioned accounts (async)
        mentioned_accounts = await self._extract_mentioned_accounts(question)
        documents = []
        person_context = ""
        
        if mentioned_accounts:
            # Build person context
            if len(mentioned_accounts) == 1:
                acc = mentioned_accounts[0]
                name_part = f" ({acc['name']})" if acc.get("name") else ""
                person_context = self.PERSON_CONTEXT_TEMPLATE.format(
                    handle=acc["handle"].lstrip("@"),
                    name_part=name_part
                )
            else:
                handles = [acc["handle"] for acc in mentioned_accounts]
                person_context = f"You are analyzing content from multiple accounts: {', '.join(handles)}.\n\n"
            
            # First, get documents from mentioned accounts
            for account in mentioned_accounts:
                account_docs = await self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=self.top_k,
                    filter_metadata={"source": account["handle"]},
                )
                documents.extend(account_docs)
            
            # Then get general context
            general_docs = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=5,
            )
            existing_ids = {d["id"] for d in documents}
            for doc in general_docs:
                if doc["id"] not in existing_ids:
                    documents.append(doc)
        else:
            documents = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=self.top_k,
            )
        
        context = self._format_context(documents)
        
        # Check if this is a price query
        price_context = ""
        if self._detect_price_query(question):
            coins = self._extract_coins(question)
            from_date, to_date, days = self._extract_time_range(question)
            price_context = await self._get_price_context(coins, from_date, to_date, days)
        
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": self.RAG_PROMPT.format(
                person_context=person_context,
                context=context, 
                price_context=price_context, 
                question=question
            )}
        ]
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                stream=True,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def _format_context(self, documents: List[dict]) -> str:
        """Format retrieved documents as context for the LLM."""
        if not documents:
            return "No relevant context found."
        
        formatted_docs = []
        for i, doc in enumerate(documents, 1):
            content = doc.get("content", "")[:500]  # Limit per document
            metadata = doc.get("metadata", {})
            source_type = metadata.get("type", "unknown")
            source = metadata.get("source", "")
            created_at = metadata.get("created_at", "")
            
            # Format date if available
            date_str = ""
            if created_at:
                try:
                    if isinstance(created_at, str):
                        # Parse and format date
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        date_str = f" [{dt.strftime('%b %d, %Y %H:%M')}]"
                except:
                    date_str = f" [{created_at}]"
            
            formatted_docs.append(
                f"[{i}] ({source_type}) {source}{date_str}\n{content}"
            )
        
        return "\n\n".join(formatted_docs)
    
    async def get_topic_summary(self, topic: str) -> dict:
        """
        Get a comprehensive summary for a specific topic/coin.
        """
        query_embedding = await embedding_service.embed_for_search(topic)
        documents = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=10,
        )
        
        if not documents:
            return {
                "topic": topic,
                "summary": "No recent data found for this topic.",
                "sentiment": "unknown",
                "sources_count": 0,
            }
        
        context = self._format_context(documents)
        
        prompt = f"""Analyze all the following content about "{topic}" and provide:
1. A comprehensive summary of what's being discussed
2. Overall sentiment (bullish/bearish/neutral)
3. Key points and trends
4. Any notable news or developments

Content:
{context}

Respond in JSON format."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a crypto analyst. Respond in JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            return {
                "topic": topic,
                "error": str(e),
                "sources_count": len(documents),
            }


# Singleton instance
rag_chain = RAGChain()
