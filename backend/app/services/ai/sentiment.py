from typing import Optional, List
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings


class SentimentResult(BaseModel):
    """Sentiment analysis result."""
    label: str  # positive, negative, neutral
    score: float  # 0.0 to 1.0
    confidence: float
    reasoning: Optional[str] = None


class SentimentAnalyzer:
    """
    AI-powered sentiment analysis for crypto content.
    
    Uses OpenAI GPT models to analyze sentiment with crypto-specific context.
    """
    
    CRYPTO_SENTIMENT_PROMPT = """You are a crypto market sentiment analyst. Analyze the following text and determine its sentiment regarding the cryptocurrency market.

Consider:
- Is this bullish (positive) or bearish (negative) for crypto?
- Market impact potential
- Overall tone and implications

Text to analyze:
{text}

Respond with a JSON object:
{{
    "label": "positive" | "negative" | "neutral",
    "score": <float 0.0 to 1.0, where 1.0 is most positive>,
    "confidence": <float 0.0 to 1.0>,
    "reasoning": "<brief explanation>"
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
    
    async def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single piece of text.
        
        Args:
            text: The text to analyze
            
        Returns:
            SentimentResult with label, score, and confidence
        """
        if not text or len(text.strip()) < 10:
            return SentimentResult(
                label="neutral",
                score=0.5,
                confidence=0.0,
                reasoning="Text too short for analysis"
            )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise sentiment analyzer. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": self.CRYPTO_SENTIMENT_PROMPT.format(text=text[:1000])
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=200,
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            return SentimentResult(
                label=result.get("label", "neutral"),
                score=float(result.get("score", 0.5)),
                confidence=float(result.get("confidence", 0.5)),
                reasoning=result.get("reasoning"),
            )
            
        except Exception as e:
            # Fallback to simple keyword-based analysis
            return self._fallback_analysis(text)
    
    async def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """Analyze sentiment of multiple texts."""
        results = []
        for text in texts:
            result = await self.analyze(text)
            results.append(result)
        return results
    
    def _fallback_analysis(self, text: str) -> SentimentResult:
        """Simple keyword-based fallback when API fails."""
        text_lower = text.lower()
        
        positive_keywords = [
            "bullish", "moon", "pump", "gains", "profit", "breakout",
            "all-time high", "ath", "buy", "long", "adoption", "partnership",
            "upgrade", "launch", "innovation", "growth"
        ]
        
        negative_keywords = [
            "bearish", "crash", "dump", "loss", "scam", "hack", "rug",
            "ban", "regulation", "sec", "lawsuit", "fear", "sell",
            "short", "decline", "correction", "fud"
        ]
        
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return SentimentResult(label="neutral", score=0.5, confidence=0.3)
        
        score = positive_count / total
        
        if score > 0.6:
            label = "positive"
        elif score < 0.4:
            label = "negative"
        else:
            label = "neutral"
        
        return SentimentResult(
            label=label,
            score=score,
            confidence=min(0.5, total * 0.1),
            reasoning="Fallback keyword analysis"
        )


# Singleton instance
sentiment_analyzer = SentimentAnalyzer()
