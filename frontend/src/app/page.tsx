"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Header } from "@/components/layout";
import { Card, CardHeader, CardTitle, CardContent, Spinner, Button, SkeletonStatsCard, SkeletonArticlesSection, SkeletonCoinsSection, SkeletonTweetsSection } from "@/components/ui";
import { StatsCard } from "@/components/stats-card";
import { SentimentGauge } from "@/components/sentiment-gauge";
import { CoinsPanel } from "@/components/coins-panel";
import { LatestArticles } from "@/components/latest-articles";
import { RecentTweets } from "@/components/tweet-card";
import { tweetsApi, pricesApi, newsApi, schedulerApi } from "@/lib/api";
import { MessageSquare, TrendingUp, TrendingDown, Users, Gauge, Download } from "lucide-react";

// Polling intervals
const HOUR_MS = 3600000; // 1 hour for news and tweets
const REALTIME_MS = 30000; // 30 seconds for prices

export default function DashboardPage() {
  // Track new items for notification
  const [newItemsCount, setNewItemsCount] = useState(0);
  const lastTweetIdRef = useRef<string | null>(null);
  const lastArticleIdRef = useRef<number | null>(null);
  const isFirstLoadRef = useRef(true);

  // Fetch dashboard stats with polling
  const {
    data: stats,
    isLoading: statsLoading,
    refetch: refetchStats
  } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => tweetsApi.getStats("24h"),
    refetchInterval: REALTIME_MS,
    staleTime: 10000,
  });

  // Fetch recent tweets - updates every hour
  const {
    data: recentTweets,
    isLoading: tweetsLoading,
    refetch: refetchTweets
  } = useQuery({
    queryKey: ["recent-tweets"],
    queryFn: () => tweetsApi.getRecent(5),
    refetchInterval: HOUR_MS,
    staleTime: HOUR_MS / 2,
  });

  // Fetch top 10 coins by market cap with real-time prices
  const {
    data: topCoins,
    isLoading: topCoinsLoading,
    refetch: refetchTopCoins,
  } = useQuery({
    queryKey: ["top-coins"],
    queryFn: () => pricesApi.getTopCoins(10),
    refetchInterval: REALTIME_MS,
    staleTime: 15000,
  });

  // Fetch trending memecoins
  const {
    data: memecoins,
    isLoading: memecoinsLoading,
    refetch: refetchMemecoins,
  } = useQuery({
    queryKey: ["memecoins"],
    queryFn: () => pricesApi.getMemecoins(10),
    refetchInterval: REALTIME_MS,
    staleTime: 15000,
  });

  // Fetch Fear & Greed Index
  const {
    data: fearGreed,
    refetch: refetchFearGreed,
  } = useQuery({
    queryKey: ["fear-greed"],
    queryFn: () => pricesApi.getFearGreedIndex(),
    refetchInterval: 300000,
    staleTime: 60000,
  });

  // Fetch latest news articles - updates every hour
  const {
    data: articles,
    isLoading: articlesLoading,
    refetch: refetchArticles,
  } = useQuery({
    queryKey: ["latest-articles"],
    queryFn: () => newsApi.getRecent(10),
    refetchInterval: HOUR_MS,
    staleTime: HOUR_MS / 2,
  });

  // Manual scrape mutation
  const scrapeMutation = useMutation({
    mutationFn: () => schedulerApi.triggerScrape("all"),
    onSuccess: () => {
      // Refetch data after scrape completes
      setTimeout(() => {
        refetchTweets();
        refetchArticles();
        refetchStats();
      }, 2000);
    },
  });

  const handleScrapeNow = () => {
    scrapeMutation.mutate();
  };

  // Track new tweets and articles for notifications
  useEffect(() => {
    if (isFirstLoadRef.current) {
      // Set initial references on first load
      if (recentTweets && recentTweets.length > 0) {
        lastTweetIdRef.current = recentTweets[0]?.id || null;
      }
      if (articles && articles.length > 0) {
        lastArticleIdRef.current = articles[0]?.id || null;
      }
      isFirstLoadRef.current = false;
      return;
    }

    let newCount = 0;

    // Check for new tweets
    if (recentTweets && recentTweets.length > 0) {
      const latestTweetId = recentTweets[0]?.id;
      if (lastTweetIdRef.current && latestTweetId !== lastTweetIdRef.current) {
        // Count how many tweets are newer than our last known
        const lastIndex = recentTweets.findIndex((t: any) => t.id === lastTweetIdRef.current);
        newCount += lastIndex > 0 ? lastIndex : recentTweets.length;
      }
    }

    // Check for new articles
    if (articles && articles.length > 0) {
      const latestArticleId = articles[0]?.id;
      if (lastArticleIdRef.current && latestArticleId !== lastArticleIdRef.current) {
        const lastIndex = articles.findIndex((a: any) => a.id === lastArticleIdRef.current);
        newCount += lastIndex > 0 ? lastIndex : articles.length;
      }
    }

    if (newCount > 0) {
      setNewItemsCount(prev => prev + newCount);
    }
  }, [recentTweets, articles]);

  const handleRefresh = () => {
    // Clear notifications and update references
    setNewItemsCount(0);
    if (recentTweets && recentTweets.length > 0) {
      lastTweetIdRef.current = recentTweets[0]?.id || null;
    }
    if (articles && articles.length > 0) {
      lastArticleIdRef.current = articles[0]?.id || null;
    }

    refetchStats();
    refetchTweets();
    refetchTopCoins();
    refetchMemecoins();
    refetchFearGreed();
    refetchArticles();
  };

  const handleNotificationClick = () => {
    // Clear notifications and refresh
    setNewItemsCount(0);
    if (recentTweets && recentTweets.length > 0) {
      lastTweetIdRef.current = recentTweets[0]?.id || null;
    }
    if (articles && articles.length > 0) {
      lastArticleIdRef.current = articles[0]?.id || null;
    }
    handleRefresh();
  };

  const isLoading = statsLoading || tweetsLoading;

  // Use actual data or fallback to defaults
  const displayStats = stats || {
    total_tweets: 0,
    tweets_24h: 0,
    bullish_percentage: 50,
    bearish_percentage: 50,
    neutral_percentage: 0,
    tracked_accounts: 0,
    sentiment_change: 0,
  };

  // Fear & Greed for sentiment gauge override (if we have external data)
  const externalSentiment = fearGreed ? {
    value: fearGreed.value,
    label: fearGreed.classification,
  } : null;

  const coinsLoading = topCoinsLoading || memecoinsLoading;

  return (
    <div className="min-h-screen">
      <Header
        title="Dashboard"
        subtitle="Real-time crypto sentiment overview"
        onRefresh={handleRefresh}
        isRefreshing={isLoading}
        notificationCount={newItemsCount}
        onNotificationClick={handleNotificationClick}
      >
        <Button
          variant="ghost"
          size="sm"
          onClick={handleScrapeNow}
          disabled={scrapeMutation.isPending}
          className="gap-2"
        >
          <Download size={16} className={scrapeMutation.isPending ? "animate-bounce" : ""} />
          {scrapeMutation.isPending ? "Scraping..." : "Scrape Now"}
        </Button>
      </Header>

      <div className="p-6 space-y-6">
        {/* Stats Cards */}
        {statsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <SkeletonStatsCard key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatsCard
              title="Total Tweets"
              value={displayStats.total_tweets}
              subtitle={`${displayStats.tweets_24h || 0} in last 24h`}
              icon={<MessageSquare size={20} />}
            />
            <StatsCard
              title="Bullish"
              value={`${displayStats.bullish_percentage}%`}
              change={displayStats.sentiment_change}
              subtitle={displayStats.tweets_24h > 0 ? `Based on ${displayStats.tweets_24h} tweets` : undefined}
              icon={<TrendingUp size={20} />}
            />
            <StatsCard
              title="Bearish"
              value={`${displayStats.bearish_percentage}%`}
              change={displayStats.sentiment_change ? -displayStats.sentiment_change : undefined}
              subtitle={displayStats.neutral_percentage > 0 ? `Neutral: ${displayStats.neutral_percentage}%` : undefined}
              icon={<TrendingDown size={20} />}
            />
            <StatsCard
              title="Tracked Accounts"
              value={displayStats.tracked_accounts}
              icon={<Users size={20} />}
            />
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Sentiment Gauge & Latest Articles */}
          <div className="lg:col-span-2 space-y-6">
            {/* Sentiment Gauge */}
            <div className="bg-surface/30 backdrop-blur-md border border-white/5 rounded-xl overflow-hidden shadow-glass">
              <div className="flex flex-row items-center justify-between p-6 pb-2">
                <h3 className="text-sm font-medium uppercase tracking-wider text-text-muted">Twitter Sentiment</h3>
                <div className="flex items-center gap-3">
                  {externalSentiment && (
                    <div className="flex items-center gap-2 text-xs font-mono text-text-muted bg-white/5 px-2 py-1 rounded">
                      <Gauge size={12} />
                      <span>Market F&G: {externalSentiment.value} ({externalSentiment.label})</span>
                    </div>
                  )}
                </div>
              </div>
              <div className="px-6 pb-6">
                <SentimentGauge
                  bullish={displayStats.bullish_percentage}
                  bearish={displayStats.bearish_percentage}
                  className="p-0 shadow-none border-0 bg-transparent"
                />
              </div>
            </div>

            {/* Latest News Articles */}
            {articlesLoading ? (
              <SkeletonArticlesSection />
            ) : (
              <LatestArticles articles={articles || []} />
            )}
          </div>

          {/* Right Column - Coins Panel & Recent Tweets */}
          <div className="space-y-6">
            {/* Crypto Prices Panel (Top 10 & Memecoins) */}
            {coinsLoading ? (
              <SkeletonCoinsSection />
            ) : (
              <CoinsPanel topCoins={topCoins || []} memecoins={memecoins || []} />
            )}

            {/* Recent Tweets */}
            {tweetsLoading ? (
              <SkeletonTweetsSection />
            ) : (
              <RecentTweets
                tweets={recentTweets || []}
                title="Recent Tweets (Latest 5)"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
