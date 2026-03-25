/**
 * Unit tests for src/lib/api.ts
 * Tests API client functions with mocked fetch.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { tweetsApi, accountsApi, pricesApi, chatApi } from "../api";

// ============ Setup: Mock fetch globally ============

const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  mockFetch.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// Helper to create a successful fetch response
function mockResponse(data: any, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    body: null,
  };
}

// ============ tweetsApi ============

describe("tweetsApi", () => {
  describe("getAll", () => {
    it("calls the correct endpoint", async () => {
      mockFetch.mockResolvedValue(
        mockResponse({ tweets: [], total: 0, limit: 20, offset: 0 })
      );

      await tweetsApi.getAll();

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const url = mockFetch.mock.calls[0][0];
      expect(url).toContain("/api/tweets");
    });

    it("transforms response to PaginatedResponse format", async () => {
      mockFetch.mockResolvedValue(
        mockResponse({
          tweets: [{ id: "1", content: "test" }],
          total: 50,
          limit: 20,
          offset: 0,
        })
      );

      const result = await tweetsApi.getAll({ page: 1, per_page: 20 });

      expect(result.items).toHaveLength(1);
      expect(result.total).toBe(50);
      expect(result.page).toBe(1);
      expect(result.per_page).toBe(20);
      expect(result.has_more).toBe(true);
    });

    it("maps sentiment filter values correctly", async () => {
      mockFetch.mockResolvedValue(
        mockResponse({ tweets: [], total: 0, limit: 20, offset: 0 })
      );

      await tweetsApi.getAll({ sentiment: "bullish" });

      const url = mockFetch.mock.calls[0][0];
      // Frontend "bullish" should map to backend "positive"
      expect(url).toContain("sentiment=positive");
    });

    it("does not send sentiment param for 'all'", async () => {
      mockFetch.mockResolvedValue(
        mockResponse({ tweets: [], total: 0, limit: 20, offset: 0 })
      );

      await tweetsApi.getAll({ sentiment: "all" });

      const url = mockFetch.mock.calls[0][0];
      expect(url).not.toContain("sentiment=");
    });
  });

  describe("getRecent", () => {
    it("calls recent endpoint with limit", async () => {
      mockFetch.mockResolvedValue(mockResponse([]));

      await tweetsApi.getRecent(5);

      const url = mockFetch.mock.calls[0][0];
      expect(url).toContain("/api/tweets/recent?limit=5");
    });
  });

  describe("search", () => {
    it("encodes query parameter", async () => {
      mockFetch.mockResolvedValue(mockResponse([]));

      await tweetsApi.search("bitcoin price");

      const url = mockFetch.mock.calls[0][0];
      expect(url).toContain("/api/search?q=bitcoin%20price");
    });
  });
});

// ============ accountsApi ============

describe("accountsApi", () => {
  describe("getAll", () => {
    it("calls accounts endpoint", async () => {
      mockFetch.mockResolvedValue(
        mockResponse({ accounts: [], total: 0 })
      );

      const result = await accountsApi.getAll();

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const url = mockFetch.mock.calls[0][0];
      expect(url).toContain("/api/tweets/accounts");
      expect(result).toEqual([]);
    });
  });

  describe("add", () => {
    it("sends POST with correct body", async () => {
      const newAccount = { handle: "VitalikButerin", category: "founder" as const };
      mockFetch.mockResolvedValue(
        mockResponse({ id: 1, ...newAccount })
      );

      await accountsApi.add(newAccount);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0];
      expect(options.method).toBe("POST");

      const body = JSON.parse(options.body);
      expect(body.handle).toBe("VitalikButerin");
      expect(body.category).toBe("founder");
    });
  });

  describe("remove", () => {
    it("sends DELETE to correct endpoint", async () => {
      mockFetch.mockResolvedValue(mockResponse(null));

      await accountsApi.remove("SomeUser");

      const [url, options] = mockFetch.mock.calls[0];
      expect(url).toContain("/api/tweets/accounts/SomeUser");
      expect(options.method).toBe("DELETE");
    });
  });
});

// ============ pricesApi ============

describe("pricesApi", () => {
  describe("getTrending", () => {
    it("slices results to limit", async () => {
      const trending = Array.from({ length: 20 }, (_, i) => ({
        id: `coin-${i}`,
        name: `Coin ${i}`,
      }));

      mockFetch.mockResolvedValue(
        mockResponse({ trending, total: 20, timestamp: "2026-01-01" })
      );

      const result = await pricesApi.getTrending(5);
      expect(result).toHaveLength(5);
    });
  });
});

// ============ Error Handling ============

describe("Error handling", () => {
  it("throws on 4xx errors", async () => {
    mockFetch.mockResolvedValue(
      mockResponse({ detail: "HTTP 400: Bad request" }, 400)
    );

    await expect(tweetsApi.getRecent()).rejects.toThrow("HTTP 400");
    // Should NOT retry on 4xx — error message starts with "HTTP 4"
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("retries on 5xx errors", async () => {
    // First two calls fail with 500, third succeeds
    mockFetch
      .mockResolvedValueOnce(mockResponse(null, 500))
      .mockResolvedValueOnce(mockResponse(null, 500))
      .mockResolvedValueOnce(mockResponse([]));

    const result = await tweetsApi.getRecent();
    expect(result).toEqual([]);
    // 1 initial + 2 retries = 3 total calls
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });

  it("includes Content-Type header", async () => {
    mockFetch.mockResolvedValue(mockResponse([]));

    await tweetsApi.getRecent();

    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers["Content-Type"]).toBe("application/json");
  });
});
