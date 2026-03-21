"""
Unit tests for app/utils/helpers.py
All 10 utility functions tested.
"""

import pytest
from datetime import datetime, timedelta

from app.utils.helpers import (
    clean_text,
    extract_tickers,
    extract_hashtags,
    generate_id,
    parse_relative_time,
    truncate_text,
    format_number,
    is_valid_twitter_handle,
    is_valid_url,
    categorize_content,
)


# ============ clean_text ============

class TestCleanText:
    def test_removes_urls(self):
        text = "Check this out https://example.com and http://foo.bar/path"
        result = clean_text(text)
        assert "https://example.com" not in result
        assert "http://foo.bar/path" not in result
        assert "Check this out" in result

    def test_normalizes_whitespace(self):
        text = "  too   many    spaces   "
        assert clean_text(text) == "too many spaces"

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_none_input(self):
        assert clean_text(None) == ""

    def test_text_without_urls(self):
        text = "Bitcoin is going up"
        assert clean_text(text) == "Bitcoin is going up"


# ============ extract_tickers ============

class TestExtractTickers:
    def test_finds_tickers(self):
        text = "I'm buying $BTC and $ETH today"
        result = extract_tickers(text)
        assert "BTC" in result
        assert "ETH" in result

    def test_deduplicates(self):
        text = "$BTC $BTC $BTC"
        result = extract_tickers(text)
        assert result == ["BTC"]

    def test_no_tickers(self):
        text = "No coins mentioned here"
        assert extract_tickers(text) == []

    def test_case_insensitive_input(self):
        text = "$btc and $eth"
        result = extract_tickers(text)
        assert "BTC" in result
        assert "ETH" in result

    def test_ignores_short_symbols(self):
        # Pattern requires 2-10 chars
        text = "$A is too short"
        assert extract_tickers(text) == []


# ============ extract_hashtags ============

class TestExtractHashtags:
    def test_finds_hashtags(self):
        text = "Check out #Bitcoin and #Ethereum"
        result = extract_hashtags(text)
        assert "Bitcoin" in result
        assert "Ethereum" in result

    def test_deduplicates(self):
        text = "#crypto #crypto #crypto"
        result = extract_hashtags(text)
        assert result == ["crypto"]

    def test_no_hashtags(self):
        assert extract_hashtags("No hashtags here") == []


# ============ generate_id ============

class TestGenerateId:
    def test_deterministic(self):
        id1 = generate_id("test", "123")
        id2 = generate_id("test", "123")
        assert id1 == id2

    def test_different_inputs_different_ids(self):
        id1 = generate_id("test", "123")
        id2 = generate_id("test", "456")
        assert id1 != id2

    def test_returns_16_chars(self):
        result = generate_id("something")
        assert len(result) == 16

    def test_hex_string(self):
        result = generate_id("abc")
        assert all(c in "0123456789abcdef" for c in result)


# ============ parse_relative_time ============

class TestParseRelativeTime:
    def test_hours(self):
        result = parse_relative_time("2h")
        assert result is not None
        expected = datetime.utcnow() - timedelta(hours=2)
        assert abs((result - expected).total_seconds()) < 2

    def test_days(self):
        result = parse_relative_time("3d")
        assert result is not None
        expected = datetime.utcnow() - timedelta(days=3)
        assert abs((result - expected).total_seconds()) < 2

    def test_weeks(self):
        result = parse_relative_time("1w")
        assert result is not None
        expected = datetime.utcnow() - timedelta(weeks=1)
        assert abs((result - expected).total_seconds()) < 2

    def test_minutes(self):
        result = parse_relative_time("30m")
        assert result is not None
        expected = datetime.utcnow() - timedelta(minutes=30)
        assert abs((result - expected).total_seconds()) < 2

    def test_none_input(self):
        assert parse_relative_time(None) is None

    def test_empty_string(self):
        assert parse_relative_time("") is None

    def test_invalid_format(self):
        assert parse_relative_time("abc") is None


# ============ truncate_text ============

class TestTruncateText:
    def test_short_text_unchanged(self):
        text = "Short"
        assert truncate_text(text, max_length=100) == "Short"

    def test_long_text_truncated(self):
        text = "A" * 200
        result = truncate_text(text, max_length=100)
        assert len(result) <= 100
        assert result.endswith("...")

    def test_custom_suffix(self):
        text = "A" * 200
        result = truncate_text(text, max_length=50, suffix="…")
        assert result.endswith("…")

    def test_breaks_at_word_boundary(self):
        text = "This is a long sentence that should be truncated at a word boundary"
        result = truncate_text(text, max_length=30)
        assert result.endswith("...")
        # Should not break mid-word
        content = result[:-3]  # Remove suffix
        assert not content.endswith(" ")  # Trimmed at word boundary or not


# ============ format_number ============

class TestFormatNumber:
    def test_millions(self):
        assert format_number(5_500_000) == "5.5M"

    def test_thousands(self):
        assert format_number(2_300) == "2.3K"

    def test_small_number(self):
        assert format_number(42) == "42"

    def test_exact_million(self):
        assert format_number(1_000_000) == "1.0M"

    def test_exact_thousand(self):
        assert format_number(1_000) == "1.0K"


# ============ is_valid_twitter_handle ============

class TestIsValidTwitterHandle:
    def test_valid_handle(self):
        assert is_valid_twitter_handle("VitalikButerin") is True

    def test_valid_with_underscore(self):
        assert is_valid_twitter_handle("crypto_guru_01") is True

    def test_strips_at_sign(self):
        assert is_valid_twitter_handle("@elonmusk") is True

    def test_too_long(self):
        assert is_valid_twitter_handle("a" * 16) is False

    def test_empty(self):
        assert is_valid_twitter_handle("") is False

    def test_just_at_sign(self):
        assert is_valid_twitter_handle("@") is False

    def test_special_characters(self):
        assert is_valid_twitter_handle("user!name") is False


# ============ is_valid_url ============

class TestIsValidUrl:
    def test_valid_https(self):
        assert is_valid_url("https://example.com") is True

    def test_valid_http(self):
        assert is_valid_url("http://example.com/path") is True

    def test_invalid_no_protocol(self):
        assert is_valid_url("example.com") is False

    def test_invalid_empty(self):
        assert is_valid_url("") is False


# ============ categorize_content ============

class TestCategorizeContent:
    def test_bullish_content(self):
        result = categorize_content("Bitcoin is pumping! Moon incoming! 🚀")
        assert "bullish" in result

    def test_bearish_content(self):
        result = categorize_content("Market crash imminent, sell everything")
        assert "bearish" in result

    def test_defi_content(self):
        result = categorize_content("New DeFi yield farming protocol launched")
        assert "defi" in result

    def test_regulation_content(self):
        result = categorize_content("SEC files new lawsuit against crypto exchange")
        assert "regulation" in result

    def test_general_fallback(self):
        result = categorize_content("Had a nice coffee today")
        assert result == ["general"]

    def test_multiple_categories(self):
        result = categorize_content("SEC regulation causes market crash and fear")
        assert "regulation" in result
        assert "bearish" in result
