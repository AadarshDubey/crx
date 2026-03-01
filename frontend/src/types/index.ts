// Tweet types - matches backend to_dict() format
export interface Tweet {
  id: string;
  content: string;
  author: {
    handle: string;
    name: string | null;
    avatar: string | null;
  };
  engagement: {
    likes: number;
    retweets: number;
    replies: number;
    views: number | null;
  };
  created_at: string;
  scraped_at: string;
  sentiment: SentimentResult | null;
  topics: string[];
  url: string | null;
  is_retweet: boolean;
  is_reply: boolean;
  // Convenience getters for compatibility
  author_handle?: string;
  author_name?: string;
  likes?: number;
  retweets?: number;
  replies?: number;
  mentioned_coins?: string[];
}

export interface SentimentResult {
  label: "bullish" | "bearish" | "neutral" | "positive" | "negative" | null;
  score: number | null;
  confidence?: number;
}

// Account types - matches backend to_dict() format
export interface TrackedAccount {
  id: number;
  handle: string;
  name: string | null;
  bio: string | null;
  avatar_url: string | null;
  category: AccountCategory;
  priority: number;
  is_active: boolean;
  followers_count: number | null;
  last_scraped_at: string | null;
  // Additional convenience fields
  tweet_count?: number;
  avg_sentiment?: number;
  last_scraped?: string;
  profile_image_url?: string;
}

export type AccountCategory =
  | "influencer"
  | "analyst"
  | "project"
  | "news"
  | "whale"
  | "developer"
  | "exchange"
  | "vc"
  | "general";

export interface AddAccountRequest {
  handle: string;
  name?: string;
  category: AccountCategory;
}

// News types
export interface NewsArticle {
  id: string;
  title: string;
  content: string;
  source: string;
  url: string;
  published_at: string;
  sentiment?: SentimentResult;
  mentioned_coins?: string[];
}

// Price types
export interface CoinPrice {
  id: string;
  symbol: string;
  name: string;
  current_price: number;
  price_change_24h: number;
  price_change_percentage_24h: number;
  market_cap: number;
  volume_24h: number;
  sparkline?: number[];
}

// Chat types
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: ChatSource[];
  isStreaming?: boolean;
}

export interface ChatSource {
  id: string;
  content: string;
  source_type: "tweet" | "news";
  url?: string;
  relevance_score: number;
}

export interface ChatRequest {
  message: string;
  use_context?: boolean;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  tokens_used: number;
}

// Analytics types
export interface SentimentDataPoint {
  timestamp: string;
  bullish: number;
  bearish: number;
  neutral: number;
  total: number;
}

export interface TweetVolumeData {
  date: string;
  count: number;
}

export interface InfluencerStats {
  handle: string;
  name: string;
  engagement: number;
  tweet_count: number;
  avg_sentiment: number;
}

export interface CoinMention {
  coin: string;
  count: number;
  percentage: number;
}

export interface HeatmapData {
  day: string;
  hour: number;
  value: number;
  sentiment: "bullish" | "bearish" | "neutral";
}

// Dashboard stats
export interface DashboardStats {
  total_tweets: number;
  bullish_percentage: number;
  bearish_percentage: number;
  neutral_percentage: number;
  tracked_accounts: number;
  tweets_24h: number;
  tweets_in_range?: number;
  sentiment_change: number;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  has_more: boolean;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// Filter types
export type TimeRange = "1h" | "24h" | "7d" | "30d";
export type SortBy = "latest" | "sentiment" | "engagement";
export type FilterSentiment = "all" | "bullish" | "bearish" | "neutral";
