import {
  Tweet,
  TrackedAccount,
  AddAccountRequest,
  ChatRequest,
  ChatResponse,
  CoinPrice,
  DashboardStats,
  SentimentDataPoint,
  PaginatedResponse,
  TimeRange,
  SortBy,
  FilterSentiment,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FETCH_TIMEOUT = 15000; // 15 seconds
const MAX_RETRIES = 2;
const RETRY_DELAYS = [1000, 2000]; // exponential backoff delays

// Generic fetch wrapper with error handling, timeout, and retry
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT);

      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        // Don't retry on 4xx client errors
        if (response.status >= 400 && response.status < 500) {
          const error = await response.json().catch(() => ({ detail: "An error occurred" }));
          throw new Error(error.detail || `HTTP ${response.status}`);
        }
        // 5xx errors are retryable
        throw new Error(`HTTP ${response.status}`);
      }

      return response.json();
    } catch (error: any) {
      lastError = error;

      // Don't retry on client errors (4xx) or aborted requests by user
      if (error.message?.startsWith("HTTP 4") || error.name === "AbortError" && attempt === 0) {
        throw error;
      }

      // Retry on network errors and 5xx
      if (attempt < MAX_RETRIES) {
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAYS[attempt]));
        continue;
      }
    }
  }

  throw lastError || new Error("Request failed after retries");
}

// ============ Tweets API ============
export const tweetsApi = {
  getAll: async (params?: {
    page?: number;
    per_page?: number;
    time_range?: TimeRange;
    sentiment?: FilterSentiment;
    account?: string;
    sort_by?: SortBy;
  }): Promise<PaginatedResponse<Tweet>> => {
    const searchParams = new URLSearchParams();

    // Convert page/per_page to offset/limit for backend
    const page = params?.page || 1;
    const perPage = params?.per_page || 20;
    const offset = (page - 1) * perPage;

    searchParams.set("limit", perPage.toString());
    searchParams.set("offset", offset.toString());

    if (params?.time_range) searchParams.set("time_range", params.time_range);
    if (params?.sentiment && params.sentiment !== "all") {
      // Map frontend sentiment values to backend format
      const sentimentMap: Record<string, string> = {
        bullish: "positive",
        bearish: "negative",
        neutral: "neutral",
      };
      searchParams.set("sentiment", sentimentMap[params.sentiment] || params.sentiment);
    }
    if (params?.account) searchParams.set("account", params.account);
    if (params?.sort_by) searchParams.set("sort_by", params.sort_by);

    const query = searchParams.toString();
    const response = await fetchApi<{
      tweets: Tweet[];
      total: number;
      limit: number;
      offset: number;
    }>(`/api/tweets${query ? `?${query}` : ""}`);

    // Transform backend response to frontend PaginatedResponse format
    return {
      items: response.tweets || [],
      total: response.total || 0,
      page: page,
      per_page: perPage,
      has_more: offset + (response.tweets?.length || 0) < (response.total || 0),
    };
  },


  getRecent: async (limit: number = 5): Promise<Tweet[]> => {
    return fetchApi<Tweet[]>(`/api/tweets/recent?limit=${limit}`);
  },

  getStats: async (time_range?: TimeRange): Promise<DashboardStats> => {
    const query = time_range ? `?time_range=${time_range}` : "";
    return fetchApi<DashboardStats>(`/api/tweets/stats${query}`);
  },

  getSentimentTimeline: async (time_range?: TimeRange): Promise<SentimentDataPoint[]> => {
    const query = time_range ? `?time_range=${time_range}` : "";
    return fetchApi<SentimentDataPoint[]>(`/api/tweets/sentiment-timeline${query}`);
  },

  search: async (query: string): Promise<Tweet[]> => {
    return fetchApi<Tweet[]>(`/api/search?q=${encodeURIComponent(query)}`);
  },
};

// ============ Accounts API ============
export const accountsApi = {
  getAll: async (): Promise<TrackedAccount[]> => {
    const response = await fetchApi<{ accounts: TrackedAccount[]; total: number }>("/api/tweets/accounts");
    return response.accounts || [];
  },

  add: async (data: AddAccountRequest): Promise<TrackedAccount> => {
    return fetchApi<TrackedAccount>("/api/tweets/accounts", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  remove: async (handle: string): Promise<void> => {
    return fetchApi<void>(`/api/tweets/accounts/${handle}`, {
      method: "DELETE",
    });
  },

  scrapeNow: async (handle: string): Promise<{ message: string }> => {
    return fetchApi<{ message: string }>(`/api/tweets/accounts/${handle}/scrape`, {
      method: "POST",
    });
  },
};

// ============ Chat API ============
export const chatApi = {
  send: async (data: ChatRequest): Promise<ChatResponse> => {
    return fetchApi<ChatResponse>("/api/chat/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Streaming chat endpoint
  streamChat: async function* (
    data: ChatRequest
  ): AsyncGenerator<string, void, unknown> {
    const url = `${API_BASE_URL}/api/chat/stream`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      yield chunk;
    }
  },
};

// ============ Prices API ============
export const pricesApi = {
  getTrending: async (limit: number = 7) => {
    const response = await fetchApi<{ trending: any[]; total: number; timestamp: string }>(
      `/api/prices/trending`
    );
    return response.trending.slice(0, limit);
  },

  getTopCoins: async (limit: number = 10) => {
    const response = await fetchApi<{ coins: any[]; total: number; timestamp: string }>(
      `/api/prices/top?limit=${limit}`
    );
    return response.coins;
  },

  getMemecoins: async (limit: number = 10) => {
    const response = await fetchApi<{ coins: any[]; total: number; timestamp: string }>(
      `/api/prices/memecoins?limit=${limit}`
    );
    return response.coins;
  },

  getFearGreedIndex: async () => {
    const response = await fetchApi<{ fear_greed: { value: number; classification: string }; timestamp: string }>(
      `/api/prices/fear-greed`
    );
    return response.fear_greed;
  },

  getBySymbol: async (symbol: string): Promise<CoinPrice> => {
    return fetchApi<CoinPrice>(`/api/prices/${symbol}`);
  },

  getMultiple: async (symbols: string[]): Promise<CoinPrice[]> => {
    return fetchApi<CoinPrice[]>(`/api/prices?symbols=${symbols.join(",")}`);
  },

  getCurrentPrices: async (coins: string[], vs_currency: string = "usd") => {
    const response = await fetchApi<{ prices: any; vs_currency: string; timestamp: string }>(
      `/api/prices/?coins=${coins.join(",")}&vs_currency=${vs_currency}`
    );
    return response.prices;
  },
};

// ============ Analytics API ============
export const analyticsApi = {
  getSentimentOverTime: async (time_range: TimeRange = "7d"): Promise<SentimentDataPoint[]> => {
    return fetchApi<SentimentDataPoint[]>(`/api/tweets/analytics/sentiment?time_range=${time_range}`);
  },

  getTweetVolume: async (time_range: TimeRange = "7d") => {
    return fetchApi<{ date: string; count: number }[]>(
      `/api/tweets/analytics/volume?time_range=${time_range}`
    );
  },

  getTopInfluencers: async (limit: number = 10) => {
    return fetchApi<{ handle: string; name: string; engagement: number }[]>(
      `/api/tweets/analytics/influencers?limit=${limit}`
    );
  },

  getCoinMentions: async (time_range: TimeRange = "7d") => {
    return fetchApi<{ coin: string; count: number; percentage: number }[]>(
      `/api/tweets/analytics/coins?time_range=${time_range}`
    );
  },

  getActivityHeatmap: async () => {
    return fetchApi<{ day: string; hour: number; count: number; intensity: number }[]>(
      "/api/tweets/analytics/heatmap"
    );
  },
};

// ============ News API ============
export const newsApi = {
  getAll: async (params?: { limit?: number; offset?: number; source?: string; category?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.offset) searchParams.set("offset", params.offset.toString());
    if (params?.source) searchParams.set("source", params.source);
    if (params?.category) searchParams.set("category", params.category);
    return fetchApi<{ articles: any[]; total: number }>(`/api/news/?${searchParams.toString()}`);
  },
  getRecent: async (limit: number = 10) => {
    const result = await fetchApi<{ articles: any[]; total: number }>(`/api/news/?limit=${limit}`);
    return result.articles || [];
  },
};

// ============ Scheduler API ============
export const schedulerApi = {
  getStatus: async () => {
    return fetchApi<{ jobs: any[]; running: boolean }>("/api/scheduler/status");
  },
  triggerScrape: async (targetType: string = "all") => {
    return fetchApi<{ status: string; results: any }>(`/api/scheduler/scrape?target_type=${targetType}`, {
      method: "POST",
    });
  },
};
