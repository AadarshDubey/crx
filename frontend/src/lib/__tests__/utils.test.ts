/**
 * Unit tests for src/lib/utils.ts
 * Tests all utility functions.
 */

import { describe, it, expect } from "vitest";
import {
  cn,
  formatNumber,
  formatPrice,
  formatPercentage,
  getSentimentColor,
  getSentimentBg,
  getSentimentDot,
  extractCoins,
  truncate,
  generateId,
} from "../utils";

// ============ cn (class merging) ============

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes", () => {
    const result = cn("base", false && "hidden", "visible");
    expect(result).toBe("base visible");
  });

  it("handles tailwind merge conflicts", () => {
    // tailwind-merge should resolve conflicts
    const result = cn("p-4", "p-2");
    expect(result).toBe("p-2");
  });

  it("handles empty input", () => {
    expect(cn()).toBe("");
  });
});

// ============ formatNumber ============

describe("formatNumber", () => {
  it("formats millions", () => {
    expect(formatNumber(5500000)).toBe("5.5M");
  });

  it("formats thousands", () => {
    expect(formatNumber(2300)).toBe("2.3k");
  });

  it("returns small numbers as-is", () => {
    expect(formatNumber(42)).toBe("42");
  });

  it("formats exact million without trailing zero", () => {
    expect(formatNumber(1000000)).toBe("1M");
  });

  it("formats exact thousand without trailing zero", () => {
    expect(formatNumber(1000)).toBe("1k");
  });
});

// ============ formatPrice ============

describe("formatPrice", () => {
  it("formats prices >= 1 with 2 decimals", () => {
    const result = formatPrice(42567.89);
    expect(result).toContain("42,567.89");
  });

  it("formats prices < 1 with up to 6 decimals", () => {
    const result = formatPrice(0.001234);
    expect(result).toContain("0.0012");
  });

  it("includes dollar sign", () => {
    const result = formatPrice(100);
    expect(result).toContain("$");
  });
});

// ============ formatPercentage ============

describe("formatPercentage", () => {
  it("adds + sign for positive values", () => {
    expect(formatPercentage(5.678)).toBe("+5.68%");
  });

  it("shows negative values with minus", () => {
    expect(formatPercentage(-3.21)).toBe("-3.21%");
  });

  it("formats zero correctly", () => {
    expect(formatPercentage(0)).toBe("0.00%");
  });

  it("skips sign when includeSign is false", () => {
    expect(formatPercentage(5.678, false)).toBe("5.68%");
  });
});

// ============ getSentimentColor ============

describe("getSentimentColor", () => {
  it("returns bullish color", () => {
    expect(getSentimentColor("bullish")).toBe("text-bullish");
  });

  it("returns bearish color", () => {
    expect(getSentimentColor("bearish")).toBe("text-bearish");
  });

  it("returns neutral by default", () => {
    expect(getSentimentColor("neutral")).toBe("text-neutral");
    expect(getSentimentColor("unknown")).toBe("text-neutral");
  });
});

// ============ getSentimentBg ============

describe("getSentimentBg", () => {
  it("returns bullish background", () => {
    expect(getSentimentBg("bullish")).toBe("bg-bullish/20 text-bullish");
  });

  it("returns bearish background", () => {
    expect(getSentimentBg("bearish")).toBe("bg-bearish/20 text-bearish");
  });

  it("returns neutral for unknown", () => {
    expect(getSentimentBg("whatever")).toBe("bg-neutral/20 text-neutral");
  });
});

// ============ getSentimentDot ============

describe("getSentimentDot", () => {
  it("returns bullish dot", () => {
    expect(getSentimentDot("bullish")).toBe("bg-bullish");
  });

  it("returns bearish dot", () => {
    expect(getSentimentDot("bearish")).toBe("bg-bearish");
  });

  it("returns neutral for default", () => {
    expect(getSentimentDot("neutral")).toBe("bg-neutral");
  });
});

// ============ extractCoins ============

describe("extractCoins", () => {
  it("extracts coin symbols", () => {
    const result = extractCoins("Buying $BTC and $ETH today!");
    expect(result).toContain("$BTC");
    expect(result).toContain("$ETH");
  });

  it("deduplicates", () => {
    const result = extractCoins("$BTC $BTC $BTC");
    expect(result).toHaveLength(1);
    expect(result[0]).toBe("$BTC");
  });

  it("returns empty for no coins", () => {
    expect(extractCoins("No coins here")).toEqual([]);
  });

  it("ignores lowercase", () => {
    // Pattern only matches uppercase $SYMBOLS
    expect(extractCoins("$btc")).toEqual([]);
  });
});

// ============ truncate ============

describe("truncate", () => {
  it("returns short text unchanged", () => {
    expect(truncate("Hello", 100)).toBe("Hello");
  });

  it("truncates long text with ellipsis", () => {
    const long = "A".repeat(200);
    const result = truncate(long, 50);
    expect(result).toHaveLength(53); // 50 + "..."
    expect(result).toMatch(/\.\.\.$/);
  });

  it("handles exact length", () => {
    expect(truncate("Hello", 5)).toBe("Hello");
  });
});

// ============ generateId ============

describe("generateId", () => {
  it("returns a string", () => {
    expect(typeof generateId()).toBe("string");
  });

  it("generates unique IDs", () => {
    const ids = new Set(Array.from({ length: 100 }, () => generateId()));
    expect(ids.size).toBe(100);
  });

  it("is non-empty", () => {
    expect(generateId().length).toBeGreaterThan(0);
  });
});
