from typing import List, Optional
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings


class Summary(BaseModel):
    """Summary result."""
    summary: str
    key_points: List[str]
    topics: List[str]
    word_count: int


class Summarizer:
    """
    AI-powered content summarization for crypto news and tweets.
    """
    
    SUMMARY_PROMPT = """Summarize the following crypto-related content concisely. Focus on:
- Key market-moving information
- Important announcements or developments
- Relevant price actions or predictions
- Any regulatory or industry news

Content:
{content}

Respond with JSON:
{{
    "summary": "<2-3 sentence summary>",
    "key_points": ["<point 1>", "<point 2>", ...],
    "topics": ["<topic 1>", "<topic 2>", ...]
}}"""

    MULTI_SUMMARY_PROMPT = """You are analyzing multiple pieces of crypto content. Create a unified summary that captures the overall narrative.

Content pieces:
{contents}

Respond with JSON:
{{
    "summary": "<comprehensive 3-4 sentence summary>",
    "key_points": ["<key insight 1>", "<key insight 2>", ...],
    "topics": ["<main topic 1>", "<main topic 2>", ...],
    "sentiment_trend": "positive" | "negative" | "mixed" | "neutral"
}}"""

    def __init__(self):
        # Use the configured LLM provider (Groq or OpenAI)
        if settings.LLM_PROVIDER.lower() == "groq" and settings.GROQ_API_KEY:
            from groq import AsyncGroq
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            self.model = settings.GROQ_MODEL
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
    
    async def summarize(self, content: str, max_length: int = 200) -> Summary:
        """
        Summarize a single piece of content.
        
        Args:
            content: The content to summarize
            max_length: Maximum summary length in words
            
        Returns:
            Summary object with summary, key points, and topics
        """
        if not content or len(content.strip()) < 50:
            return Summary(
                summary=content,
                key_points=[],
                topics=[],
                word_count=len(content.split())
            )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a crypto news summarizer. Keep summaries under {max_length} words."
                    },
                    {
                        "role": "user",
                        "content": self.SUMMARY_PROMPT.format(content=content[:3000])
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500,
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            return Summary(
                summary=result.get("summary", ""),
                key_points=result.get("key_points", []),
                topics=result.get("topics", []),
                word_count=len(result.get("summary", "").split())
            )
            
        except Exception as e:
            # Fallback: return first few sentences
            sentences = content.split(". ")[:3]
            return Summary(
                summary=". ".join(sentences) + ".",
                key_points=[],
                topics=[],
                word_count=len(" ".join(sentences).split())
            )
    
    async def summarize_batch(
        self, 
        contents: List[str], 
        create_unified: bool = False
    ) -> List[Summary] | Summary:
        """
        Summarize multiple pieces of content.
        
        Args:
            contents: List of content strings
            create_unified: If True, create single unified summary
            
        Returns:
            List of summaries or single unified summary
        """
        if create_unified:
            return await self._create_unified_summary(contents)
        
        results = []
        for content in contents:
            result = await self.summarize(content)
            results.append(result)
        return results
    
    async def _create_unified_summary(self, contents: List[str]) -> Summary:
        """Create a unified summary from multiple content pieces."""
        # Truncate each content to fit in context
        max_per_content = 500
        truncated = [c[:max_per_content] for c in contents[:10]]
        formatted = "\n\n---\n\n".join(
            f"[{i+1}] {content}" 
            for i, content in enumerate(truncated)
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a crypto market analyst creating comprehensive summaries."
                    },
                    {
                        "role": "user",
                        "content": self.MULTI_SUMMARY_PROMPT.format(contents=formatted)
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=600,
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            return Summary(
                summary=result.get("summary", ""),
                key_points=result.get("key_points", []),
                topics=result.get("topics", []),
                word_count=len(result.get("summary", "").split())
            )
            
        except Exception as e:
            return Summary(
                summary="Failed to create unified summary",
                key_points=[],
                topics=[],
                word_count=0
            )


# Singleton instance
summarizer = Summarizer()
