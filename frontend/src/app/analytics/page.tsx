"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Header } from "@/components/layout";
import { Card, CardHeader, CardTitle, CardContent, Select, Spinner, Button } from "@/components/ui";
import {
  SentimentTimeline,
  TweetVolumeChart,
  CoinMentionsChart,
  ActivityHeatmap,
} from "@/components/charts";
import { analyticsApi } from "@/lib/api";
import { TimeRange } from "@/types";
import { cn, formatNumber } from "@/lib/utils";
import { RefreshCw, TrendingUp, TrendingDown, Users, Coins, Activity } from "lucide-react";

const timeRangeOptions = [
  { value: "24h", label: "24 Hours" },
  { value: "7d", label: "7 Days" },
  { value: "30d", label: "30 Days" },
];

const AUTO_REFRESH_INTERVAL = 60000; // 60 seconds

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>("7d");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [mounted, setMounted] = useState(false);

  // Only set time after mount to avoid hydration mismatch
  useEffect(() => {
    setMounted(true);
    setLastUpdated(new Date());
  }, []);

  // Fetch real analytics data from API
  const {
    data: sentimentData,
    isLoading: sentimentLoading,
    error: sentimentError,
    refetch: refetchSentiment,
  } = useQuery({
    queryKey: ["analytics-sentiment", timeRange],
    queryFn: () => analyticsApi.getSentimentOverTime(timeRange),
    refetchInterval: AUTO_REFRESH_INTERVAL,
    staleTime: 30000,
  });

  const {
    data: volumeData,
    isLoading: volumeLoading,
    error: volumeError,
    refetch: refetchVolume,
  } = useQuery({
    queryKey: ["analytics-volume", timeRange],
    queryFn: () => analyticsApi.getTweetVolume(timeRange),
    refetchInterval: AUTO_REFRESH_INTERVAL,
    staleTime: 30000,
  });

  const {
    data: influencers,
    isLoading: influencersLoading,
    error: influencersError,
    refetch: refetchInfluencers,
  } = useQuery({
    queryKey: ["analytics-influencers"],
    queryFn: () => analyticsApi.getTopInfluencers(10),
    refetchInterval: AUTO_REFRESH_INTERVAL,
    staleTime: 30000,
  });

  const {
    data: coinMentions,
    isLoading: coinsLoading,
    error: coinsError,
    refetch: refetchCoins,
  } = useQuery({
    queryKey: ["analytics-coins", timeRange],
    queryFn: () => analyticsApi.getCoinMentions(timeRange),
    refetchInterval: AUTO_REFRESH_INTERVAL,
    staleTime: 30000,
  });

  const {
    data: heatmapData,
    isLoading: heatmapLoading,
    error: heatmapError,
    refetch: refetchHeatmap,
  } = useQuery({
    queryKey: ["analytics-heatmap"],
    queryFn: analyticsApi.getActivityHeatmap,
    refetchInterval: AUTO_REFRESH_INTERVAL,
    staleTime: 30000,
  });

  // Update last updated time when data fetches
  useEffect(() => {
    if (sentimentData || volumeData || influencers || coinMentions) {
      setLastUpdated(new Date());
    }
  }, [sentimentData, volumeData, influencers, coinMentions]);

  const handleRefreshAll = () => {
    refetchSentiment();
    refetchVolume();
    refetchInfluencers();
    refetchCoins();
    refetchHeatmap();
    setLastUpdated(new Date());
  };

  const isLoading = sentimentLoading || volumeLoading;
  const hasAnyData = sentimentData || volumeData || influencers || coinMentions || heatmapData;

  // Calculate summary stats from real data
  const summaryStats = {
    avgBullish: sentimentData?.length
      ? Math.round(sentimentData.reduce((sum: number, d: any) => sum + d.bullish, 0) / sentimentData.length)
      : 0,
    totalTweets: volumeData?.reduce((sum: number, d: any) => sum + d.count, 0) || 0,
    topInfluencer: influencers?.[0]?.handle || "N/A",
    topCoin: coinMentions?.[0]?.coin || "N/A",
  };

  return (
    <div className="min-h-screen bg-background">
      <Header title="Analytics" subtitle="Sentiment analysis and trends">
        <div className="flex items-center gap-3">
          {/* Last Updated */}
          <span className="text-xs text-text-muted hidden sm:inline" suppressHydrationWarning>
            {mounted && lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Loading...'}
          </span>

          {/* Time Range Selector */}
          <Select
            options={timeRangeOptions}
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as TimeRange)}
          />

          {/* Refresh Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefreshAll}
            className="gap-2"
          >
            <RefreshCw size={14} className={cn(isLoading && "animate-spin")} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        </div>
      </Header>

      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Summary Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-bullish/10 to-bullish/5 border-bullish/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-bullish/20">
                  <TrendingUp size={20} className="text-bullish" />
                </div>
                <div>
                  <p className="text-xs text-text-muted">Avg Bullish</p>
                  <p className="text-2xl font-bold text-bullish">{summaryStats.avgBullish}%</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-primary/10 to-primary/5 border-primary/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/20">
                  <Activity size={20} className="text-primary" />
                </div>
                <div>
                  <p className="text-xs text-text-muted">Total Tweets</p>
                  <p className="text-2xl font-bold text-primary">{formatNumber(summaryStats.totalTweets)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-accent/10 to-accent/5 border-accent/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-accent/20">
                  <Users size={20} className="text-accent" />
                </div>
                <div>
                  <p className="text-xs text-text-muted">Top Influencer</p>
                  <p className="text-lg font-bold text-accent truncate">@{summaryStats.topInfluencer}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-warning/10 to-warning/5 border-warning/20">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-warning/20">
                  <Coins size={20} className="text-warning" />
                </div>
                <div>
                  <p className="text-xs text-text-muted">Most Mentioned</p>
                  <p className="text-2xl font-bold text-warning">${summaryStats.topCoin}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Top Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sentiment Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <TrendingUp size={16} className="text-bullish" />
                Sentiment Over Time
              </CardTitle>
              <p className="text-xs text-text-muted">Bullish vs Bearish trends</p>
            </CardHeader>
            <CardContent>
              {sentimentLoading ? (
                <div className="flex justify-center py-12">
                  <Spinner />
                </div>
              ) : sentimentError ? (
                <div className="py-12 text-center text-text-muted">
                  <p>Failed to load sentiment data</p>
                  <Button variant="ghost" size="sm" onClick={() => refetchSentiment()} className="mt-2">
                    Retry
                  </Button>
                </div>
              ) : sentimentData && sentimentData.length > 0 ? (
                <SentimentTimeline
                  data={sentimentData}
                  title=""
                />
              ) : (
                <div className="py-12 text-center text-text-muted">
                  No sentiment data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tweet Volume */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Activity size={16} className="text-primary" />
                Tweet Volume
              </CardTitle>
              <p className="text-xs text-text-muted">Daily tweet activity</p>
            </CardHeader>
            <CardContent>
              {volumeLoading ? (
                <div className="flex justify-center py-12">
                  <Spinner />
                </div>
              ) : volumeError ? (
                <div className="py-12 text-center text-text-muted">
                  <p>Failed to load volume data</p>
                  <Button variant="ghost" size="sm" onClick={() => refetchVolume()} className="mt-2">
                    Retry
                  </Button>
                </div>
              ) : volumeData && volumeData.length > 0 ? (
                <TweetVolumeChart
                  data={volumeData}
                  title=""
                />
              ) : (
                <div className="py-12 text-center text-text-muted">
                  No volume data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Middle Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Top Influencers */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Users size={16} className="text-accent" />
                Top Influencers
              </CardTitle>
              <p className="text-xs text-text-muted">By total engagement</p>
            </CardHeader>
            <CardContent className="p-0">
              {influencersLoading ? (
                <div className="flex justify-center py-8">
                  <Spinner />
                </div>
              ) : influencersError ? (
                <div className="py-8 text-center text-text-muted">
                  <p>Failed to load influencers</p>
                  <Button variant="ghost" size="sm" onClick={() => refetchInfluencers()} className="mt-2">
                    Retry
                  </Button>
                </div>
              ) : influencers && influencers.length > 0 ? (
                <div className="divide-y divide-border">
                  {influencers.map((inf: { handle: string; name: string; engagement: number }, index: number) => (
                    <div
                      key={inf.handle}
                      className="flex items-center justify-between px-4 py-3 hover:bg-surface-light/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className={cn(
                          "text-sm font-bold w-6 h-6 rounded-full flex items-center justify-center",
                          index === 0 ? "bg-warning/20 text-warning" :
                            index === 1 ? "bg-text-muted/20 text-text-secondary" :
                              index === 2 ? "bg-warning/10 text-warning/70" :
                                "bg-surface-light text-text-muted"
                        )}>
                          {index + 1}
                        </span>
                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/30 to-accent/30 flex items-center justify-center">
                          <span className="text-xs font-bold text-primary">
                            {inf.handle[0]?.toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-text-primary text-sm">
                            @{inf.handle}
                          </p>
                          {inf.name && inf.name !== inf.handle && (
                            <p className="text-xs text-text-muted">{inf.name}</p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-medium text-text-secondary">
                          {formatNumber(inf.engagement)}
                        </span>
                        <p className="text-xs text-text-muted">engagement</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-text-muted">
                  No influencer data available
                </div>
              )}
            </CardContent>
          </Card>

          {/* Coin Mentions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Coins size={16} className="text-warning" />
                Coin Mentions
              </CardTitle>
              <p className="text-xs text-text-muted">Most mentioned cryptocurrencies</p>
            </CardHeader>
            <CardContent>
              {coinsLoading ? (
                <div className="flex justify-center py-12">
                  <Spinner />
                </div>
              ) : coinsError ? (
                <div className="py-12 text-center text-text-muted">
                  <p>Failed to load coin data</p>
                  <Button variant="ghost" size="sm" onClick={() => refetchCoins()} className="mt-2">
                    Retry
                  </Button>
                </div>
              ) : coinMentions && coinMentions.length > 0 ? (
                <CoinMentionsChart
                  data={coinMentions}
                  title=""
                />
              ) : (
                <div className="py-12 text-center text-text-muted">
                  No coin mention data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Activity Heatmap */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity size={16} className="text-primary" />
              Tweet Activity Heatmap
            </CardTitle>
            <p className="text-xs text-text-muted">
              When are influencers most active? (based on tweet timestamps)
            </p>
          </CardHeader>
          <CardContent>
            {heatmapLoading ? (
              <div className="flex justify-center py-12">
                <Spinner />
              </div>
            ) : heatmapError ? (
              <div className="py-12 text-center text-text-muted">
                <p>Failed to load activity data</p>
                <Button variant="ghost" size="sm" onClick={() => refetchHeatmap()} className="mt-2">
                  Retry
                </Button>
              </div>
            ) : heatmapData && heatmapData.length > 0 ? (
              <ActivityHeatmap
                data={heatmapData}
                title=""
              />
            ) : (
              <div className="py-12 text-center text-text-muted">
                No activity data available
              </div>
            )}
          </CardContent>
        </Card>

        {/* Auto-refresh indicator */}
        <div className="text-center text-xs text-text-muted py-4">
          <span className="inline-flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-bullish opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-bullish"></span>
            </span>
            Auto-refreshing every 60 seconds{mounted && lastUpdated ? ` · Last updated: ${lastUpdated.toLocaleTimeString()}` : ''}
          </span>
        </div>
      </div>
    </div>
  );
}
