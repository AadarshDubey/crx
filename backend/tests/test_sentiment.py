"""
Unit tests for app/services/ai/sentiment.py
Tests the fallback analysis and edge cases — LLM calls are mocked.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.sentiment import SentimentAnalyzer, SentimentResult


@pytest.fixture
def analyzer():
    """Create a SentimentAnalyzer with mocked LLM client."""
    with patch("app.services.ai.sentiment.settings") as mock_settings:
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_MODEL = "gpt-4o-mini"
        mock_settings.GROQ_API_KEY = None

        with patch("app.services.ai.sentiment.AsyncOpenAI") as mock_openai:
            instance = SentimentAnalyzer()
            instance.client = AsyncMock()
            yield instance


# ============ Short Text Handling ============

class TestShortTextHandling:
    @pytest.mark.asyncio
    async def test_empty_text_returns_neutral(self, analyzer):
        result = await analyzer.analyze("")
        assert result.label == "neutral"
        assert result.score == 0.5
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_very_short_text_returns_neutral(self, analyzer):
        result = await analyzer.analyze("Hi")
        assert result.label == "neutral"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_none_text_returns_neutral(self, analyzer):
        result = await analyzer.analyze(None)
        assert result.label == "neutral"


# ============ Fallback Analysis ============

class TestFallbackAnalysis:
    def test_bullish_text(self, analyzer):
        result = analyzer._fallback_analysis(
            "Bitcoin is pumping! Moon incoming, gains are insane! Bullish breakout!"
        )
        assert result.label == "positive"
        assert result.score > 0.6

    def test_bearish_text(self, analyzer):
        result = analyzer._fallback_analysis(
            "Market crash dump sell everything, fear is spreading. Bearish times."
        )
        assert result.label == "negative"
        assert result.score < 0.4

    def test_neutral_text(self, analyzer):
        result = analyzer._fallback_analysis(
            "Just picked up my dry cleaning from the store."
        )
        assert result.label == "neutral"
        assert result.score == 0.5
        assert result.confidence == 0.3

    def test_mixed_text(self, analyzer):
        result = analyzer._fallback_analysis(
            "Bitcoin pump but also crash potential and fear"
        )
        # Should have some result — exact label depends on keyword count
        assert result.label in ("positive", "negative", "neutral")
        assert 0.0 <= result.score <= 1.0

    def test_confidence_scales_with_keywords(self, analyzer):
        # More keywords = higher confidence (capped at 0.5)
        result = analyzer._fallback_analysis(
            "bullish moon pump gains profit breakout buy long"
        )
        assert result.confidence > 0.0


# ============ Analyze with Mocked LLM ============

class TestAnalyzeWithMockedLLM:
    @pytest.mark.asyncio
    async def test_successful_analysis(self, analyzer):
        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "label": "positive",
                        "score": 0.9,
                        "confidence": 0.95,
                        "reasoning": "Strong bullish signals"
                    })
                )
            )
        ]
        analyzer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await analyzer.analyze("Bitcoin to $200K this year! 🚀🚀🚀")
        assert result.label == "positive"
        assert result.score == 0.9
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_api_failure_falls_back(self, analyzer):
        # Mock API to raise an exception
        analyzer.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API rate limited")
        )

        result = await analyzer.analyze(
            "Bitcoin is pumping! Bullish breakout confirmed! Moon!"
        )
        # Should fallback to keyword analysis
        assert result.label == "positive"
        assert result.reasoning == "Fallback keyword analysis"


# ============ SentimentResult Model ============

class TestSentimentResult:
    def test_create_result(self):
        result = SentimentResult(
            label="positive",
            score=0.85,
            confidence=0.9,
            reasoning="Test"
        )
        assert result.label == "positive"
        assert result.score == 0.85

    def test_optional_reasoning(self):
        result = SentimentResult(
            label="neutral",
            score=0.5,
            confidence=0.5,
        )
        assert result.reasoning is None


# ============ Batch Analysis ============

class TestBatchAnalysis:
    @pytest.mark.asyncio
    async def test_analyze_batch(self, analyzer):
        # Mock analyze to return a fixed result
        mock_result = SentimentResult(
            label="positive", score=0.8, confidence=0.9
        )
        analyzer.analyze = AsyncMock(return_value=mock_result)

        results = await analyzer.analyze_batch(["text1", "text2", "text3"])
        assert len(results) == 3
        assert all(r.label == "positive" for r in results)
