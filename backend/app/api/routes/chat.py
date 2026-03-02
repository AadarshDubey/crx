from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Tuple, Any
from datetime import datetime
import json
import asyncio
import traceback

from app.config import settings
from app.services.ai.rag_chain import rag_chain
from app.services.scrapers.twitter_scraper import TwitterScraper
from app.database.connection import async_session
from app.models.tweet import Tweet
from app.models.account import TrackedAccount
from app.services.ai.embeddings import embedding_service
from app.services.ai.sentiment import sentiment_analyzer
from app.database.vector_store import get_vector_store
from sqlalchemy import select

router = APIRouter()
twitter_scraper = TwitterScraper()


def _get_llm_client() -> Tuple[Any, str]:
    """Get the configured LLM client and model name."""
    if settings.LLM_PROVIDER.lower() == "groq" and settings.GROQ_API_KEY:
        from groq import AsyncGroq
        return AsyncGroq(api_key=settings.GROQ_API_KEY), settings.GROQ_MODEL
    else:
        from openai import AsyncOpenAI
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY), settings.OPENAI_MODEL


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat request with conversation history."""
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    use_context: bool = True  # Whether to use RAG with scraped data


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    sources: List[dict] = []
    sentiment_summary: Optional[dict] = None


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with AI about crypto news and sentiment.
    
    Uses RAG to answer questions based on scraped tweets and news.
    
    Example queries:
    - "What's the sentiment on Bitcoin today?"
    - "Summarize the latest news about Ethereum"
    - "What are crypto influencers saying about the market?"
    """
    try:
        # Convert conversation history to the format expected by RAG chain
        history = None
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        # Use RAG if context is enabled, otherwise just chat
        if request.use_context:
            result = await rag_chain.query(
                question=request.message,
                conversation_history=history,
            )
            return ChatResponse(
                response=result.answer,
                sources=[
                    {
                        "id": s.id,
                        "content": s.content,
                        "type": s.source_type,
                        "url": s.url,
                        "relevance": s.relevance_score,
                    }
                    for s in result.sources
                ],
                sentiment_summary=None,
            )
        else:
            # Direct chat without RAG context
            client, model = _get_llm_client()
            
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful crypto market analyst."},
                    {"role": "user", "content": request.message}
                ],
                max_tokens=800,
            )
            return ChatResponse(
                response=response.choices[0].message.content,
                sources=[],
                sentiment_summary=None,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat response with progress updates.
    
    Returns server-sent events with:
    - status: Progress updates (detecting accounts, scraping, analyzing)
    - chunk: Response text chunks
    - sources: Source documents used
    - done: Completion signal
    """
    async def generate():
        try:
            question = request.message
            fresh_tweets_context = []  # Store freshly scraped tweets for direct LLM use
            
            # Step 1: Detect mentioned accounts
            yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing your question...'})}\n\n"
            await asyncio.sleep(0.2)
            
            mentioned_accounts = await rag_chain._extract_mentioned_accounts(question)
            
            scraped_any = False
            if mentioned_accounts:
                handles = [acc["handle"].lstrip("@") for acc in mentioned_accounts]
                yield f"data: {json.dumps({'type': 'status', 'message': f'Detected accounts: {", ".join(["@" + h for h in handles])}'})}\n\n"
                await asyncio.sleep(0.2)
                
                # Step 2: Ensure accounts are in tracking list
                async with async_session() as db:
                    for handle in handles:
                        # Check if account exists
                        existing = await db.execute(
                            select(TrackedAccount).where(TrackedAccount.handle == handle)
                        )
                        if not existing.scalar_one_or_none():
                            # Add new account to tracking list
                            new_account = TrackedAccount(
                                handle=handle,
                                category="influencer",  # Default category
                                priority=1,
                                is_active=True,
                            )
                            db.add(new_account)
                            await db.commit()
                            yield f"data: {json.dumps({'type': 'status', 'message': f'Added @{handle} to tracking list'})}\n\n"
                            await asyncio.sleep(0.1)
                
                # Step 3: Scrape fresh data for each account
                for acc in mentioned_accounts:
                    handle = acc["handle"].lstrip("@")
                    
                    yield f"data: {json.dumps({'type': 'status', 'message': f'Fetching latest tweets from @{handle}...'})}\n\n"
                    
                    try:
                        # Scrape tweets - get fresh data from Twitter
                        scraped_items = await twitter_scraper.scrape(
                            target=handle,
                            max_tweets=15,
                            include_replies=False,
                            include_retweets=False,
                        )
                        
                        if scraped_items:
                            # Show the timestamp of the most recent tweet
                            latest_time = scraped_items[0].created_at.strftime("%b %d, %H:%M") if scraped_items[0].created_at else "Unknown"
                            yield f"data: {json.dumps({'type': 'status', 'message': f'Found {len(scraped_items)} tweets (latest: {latest_time})'})}\n\n"
                            
                            # Add to fresh context for direct LLM use
                            for item in scraped_items[:10]:  # Use top 10 most recent
                                fresh_tweets_context.append({
                                    "handle": handle,
                                    "content": item.content,
                                    "created_at": item.created_at.isoformat() if item.created_at else "Unknown",
                                    "url": item.url,
                                })
                            
                            # Also store in database and vector store for future use
                            try:
                                async with async_session() as db:
                                    vector_store = get_vector_store()
                                    stored_count = 0
                                    
                                    for item in scraped_items[:15]:
                                        # Check if tweet already exists
                                        existing = await db.execute(
                                            select(Tweet.id).where(Tweet.id == item.id)
                                        )
                                        if existing.scalar_one_or_none():
                                            continue
                                        
                                        # Analyze sentiment
                                        try:
                                            sentiment_result = await sentiment_analyzer.analyze(item.content)
                                        except:
                                            sentiment_result = {"score": 0, "label": "neutral"}
                                        
                                        # Create tweet record
                                        tweet = Tweet(
                                            id=item.id,
                                            author_handle=handle,
                                            author_name=item.metadata.get("author_name", handle),
                                            content=item.content,
                                            tweet_created_at=item.created_at,
                                            scraped_at=datetime.utcnow(),
                                            likes=item.metadata.get("likes", 0),
                                            retweets=item.metadata.get("retweets", 0),
                                            replies=item.metadata.get("replies", 0),
                                            url=item.url,
                                            sentiment_score=sentiment_result.get("score", 0),
                                            sentiment_label=sentiment_result.get("label", "neutral"),
                                        )
                                        db.add(tweet)
                                        
                                        # Store embedding
                                        try:
                                            embedding = await embedding_service.embed_for_storage(item.content)
                                            await vector_store.add_documents( # Added await here
                                                documents=[item.content],
                                                embeddings=[embedding],
                                                metadatas=[{
                                                    "id": item.id,
                                                    "source": f"@{handle}",
                                                    "source_type": "tweet",
                                                    "url": item.url,
                                                    "created_at": item.created_at.isoformat() if item.created_at else "",
                                                    "sentiment": sentiment_result.get("label", "neutral"),
                                                }],
                                                ids=[item.id],
                                            )
                                            stored_count += 1
                                        except Exception:
                                            pass
                                    
                                    await db.commit()
                                    
                                    if stored_count > 0:
                                        scraped_any = True
                                        yield f"data: {json.dumps({'type': 'status', 'message': f'Indexed {stored_count} new tweets'})}\n\n"
                                    else:
                                        yield f"data: {json.dumps({'type': 'status', 'message': f'Tweets already in database'})}\n\n"
                            except Exception as db_error:
                                yield f"data: {json.dumps({'type': 'status', 'message': f'Using fresh tweets directly'})}\n\n"
                        else:
                            yield f"data: {json.dumps({'type': 'status', 'message': f'No tweets found for @{handle}'})}\n\n"
                        
                    except Exception as e:
                        error_msg = str(e)[:100]  # Truncate long errors
                        yield f"data: {json.dumps({'type': 'status', 'message': f'Scraping error: {error_msg}'})}\n\n"
                        yield f"data: {json.dumps({'type': 'status', 'message': f'Falling back to cached data for @{handle}'})}\n\n"
                    
                    await asyncio.sleep(0.1)
            
            # Step 4: Generate response
            yield f"data: {json.dumps({'type': 'status', 'message': 'Generating analysis...'})}\n\n"
            await asyncio.sleep(0.2)
            
            # Build context from fresh tweets if available
            if fresh_tweets_context:
                # Create a direct prompt with fresh tweets
                tweets_text = "\n\n".join([
                    f"Tweet from @{t['handle']} ({t['created_at']}):\n\"{t['content']}\"\nURL: {t['url']}"
                    for t in fresh_tweets_context
                ])
                
                # Use LLM directly with fresh tweets
                client, model = _get_llm_client()
                
                system_prompt = """You are an expert crypto market analyst. Analyze the provided tweets and answer the user's question.

When analyzing tweets:
1. Focus on the MOST RECENT tweets first (check the timestamps)
2. Identify the overall sentiment (bullish/bearish/neutral)
3. Highlight key themes and notable statements
4. Quote or paraphrase specific tweets when relevant
5. Assess potential market impact

Be specific and reference the actual content of the tweets."""

                user_prompt = f"""Here are the latest tweets I just scraped:

{tweets_text}

User Question: {question}

Please provide a comprehensive analysis based on these fresh tweets. Start with the most recent tweets."""

                # Build messages with conversation history for multi-turn context
                messages = [{"role": "system", "content": system_prompt}]
                if request.conversation_history:
                    for msg in request.conversation_history[-6:]:
                        messages.append({"role": msg.role, "content": msg.content})
                messages.append({"role": "user", "content": user_prompt})

                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1500,
                    temperature=0.7,
                )
                
                answer = response.choices[0].message.content
                
                # Stream the response
                words = answer.split(' ')
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i+chunk_size]) + ' '
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.03)
                
                # Send sources from fresh tweets
                sources = [
                    {
                        "id": f"fresh_{i}",
                        "content": t["content"][:100] + "..." if len(t["content"]) > 100 else t["content"],
                        "source_type": "tweet",
                        "url": t["url"],
                    }
                    for i, t in enumerate(fresh_tweets_context[:5])
                ]
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            else:
                # Fall back to RAG if no fresh tweets
                result = await rag_chain.query(
                    question=question,
                    conversation_history=[
                        {"role": msg.role, "content": msg.content}
                        for msg in (request.conversation_history or [])
                    ],
                )
                
                # Stream the response
                words = result.answer.split(' ')
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk = ' '.join(words[i:i+chunk_size]) + ' '
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.03)
                
                # Send sources
                sources = [
                    {
                        "id": s.id,
                        "content": s.content[:100] + "..." if len(s.content) > 100 else s.content,
                        "source_type": s.source_type,
                        "url": s.url,
                    }
                    for s in result.sources[:5]
                ]
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            
            # Done
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            error_detail = traceback.format_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/suggestions")
async def get_chat_suggestions():
    """Get suggested questions for the chat interface."""
    return {
        "suggestions": [
            "What's the overall market sentiment today?",
            "Summarize the top crypto news from the last 24 hours",
            "What are people saying about Bitcoin?",
            "Are there any concerning regulatory news?",
            "What's trending in DeFi right now?",
            "Give me a bullish/bearish breakdown for Ethereum",
        ]
    }


@router.post("/analyze")
async def analyze_topic(topic: str):
    """
    Get detailed AI analysis of a specific topic/coin.
    
    Combines sentiment analysis, news summary, and social signals.
    """
    try:
        result = await rag_chain.get_topic_summary(topic)
        return {
            "topic": topic,
            "analysis": result,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
