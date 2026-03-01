"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LiveFeedHeader } from "@/components/live-feed-header";
import { FeedFilterBar } from "@/components/feed-filter-bar";
import { NewTweetsBanner } from "@/components/new-tweets-banner";
import { TweetCard } from "@/components/tweet-card";
import { Card, CardContent, Spinner, Button } from "@/components/ui";
import { tweetsApi, accountsApi } from "@/lib/api";
import { Tweet, TrackedAccount, TimeRange, SortBy, FilterSentiment } from "@/types";
import { ArrowDown, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const POLL_INTERVAL = 30000; // 30 seconds

export default function FeedPage() {
  const queryClient = useQueryClient();

  // Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [timeRange, setTimeRange] = useState<TimeRange>("24h");
  const [sentiment, setSentiment] = useState<FilterSentiment>("all");
  const [sortBy, setSortBy] = useState<SortBy>("latest");
  const [selectedAccount, setSelectedAccount] = useState<string>("");
  const [page, setPage] = useState(1);

  // UI state
  const [newTweetsCount, setNewTweetsCount] = useState(0);
  const [selectedTweets, setSelectedTweets] = useState<Set<string>>(new Set());
  const [isLive, setIsLive] = useState(true);
  const lastTweetIdRef = useRef<string | null>(null);
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Fetch accounts for filter
  const { data: accounts } = useQuery({
    queryKey: ["accounts"],
    queryFn: accountsApi.getAll,
  });

  // Fetch tweets
  const {
    data: tweetsData,
    isLoading,
    refetch,
    isFetching,
    isError,
  } = useQuery({
    queryKey: ["tweets", timeRange, sentiment, sortBy, selectedAccount, page],
    queryFn: () =>
      tweetsApi.getAll({
        time_range: timeRange,
        sentiment: sentiment,
        sort_by: sortBy,
        account: selectedAccount || undefined,
        page,
        per_page: 20,
      }),
    refetchInterval: POLL_INTERVAL,
    staleTime: 10000,
  });

  // Search tweets
  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ["tweet-search", searchQuery],
    queryFn: () => tweetsApi.search(searchQuery),
    enabled: searchQuery.length > 2,
  });

  // Check for new tweets on poll
  useEffect(() => {
    if (tweetsData?.items?.length && page === 1) {
      const latestTweetId = tweetsData.items[0]?.id;

      if (lastTweetIdRef.current && latestTweetId !== lastTweetIdRef.current) {
        // Find how many new tweets
        const lastIndex = tweetsData.items.findIndex(
          (t: Tweet) => t.id === lastTweetIdRef.current
        );
        if (lastIndex > 0) {
          setNewTweetsCount(lastIndex);
        }
      }

      // Only update ref after initial load
      if (!newTweetsCount) {
        lastTweetIdRef.current = latestTweetId;
      }
    }
  }, [tweetsData, page, newTweetsCount]);

  // Handle live status based on last successful fetch
  useEffect(() => {
    if (isError) {
      setIsLive(false);
    } else if (tweetsData) {
      setIsLive(true);
    }
  }, [isError, tweetsData]);

  const loadNewTweets = useCallback(() => {
    setNewTweetsCount(0);
    if (tweetsData?.items?.length) {
      lastTweetIdRef.current = tweetsData.items[0]?.id;
    }
    refetch();
  }, [refetch, tweetsData]);

  const handleRefresh = useCallback(() => {
    setPage(1);
    setNewTweetsCount(0);
    refetch();
  }, [refetch]);

  const loadMore = useCallback(() => {
    if (tweetsData?.has_more) {
      setPage((prev) => prev + 1);
    }
  }, [tweetsData?.has_more]);

  const handleTweetSelect = useCallback((id: string, selected: boolean) => {
    setSelectedTweets((prev) => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(id);
      } else {
        newSet.delete(id);
      }
      return newSet;
    });
  }, []);

  // Ref for scroll container
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Intersection Observer for infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && tweetsData?.has_more && !isFetching) {
          loadMore();
        }
      },
      {
        threshold: 0.1,
        root: scrollContainerRef.current
      }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
  }, [tweetsData?.has_more, isFetching, loadMore, scrollContainerRef.current]);

  const accountsList = Array.isArray(accounts) ? accounts : [];
  const displayTweets = searchQuery.length > 2 ? searchResults : tweetsData?.items;

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Live Feed Header - Fixed at top */}
      <div className="flex-none z-20 bg-background/95 backdrop-blur-sm border-b border-border">
        <LiveFeedHeader
          tweetCount={tweetsData?.total || 0}
          isLive={isLive}
          onRefresh={handleRefresh}
          isRefreshing={isFetching}
        />

        {/* Filters Bar - Also fixed */}
        <div className="bg-background/95 backdrop-blur-sm px-6 py-2 border-b border-border/50">
          <FeedFilterBar
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
            timeRange={timeRange}
            onTimeRangeChange={(range) => { setTimeRange(range); setPage(1); }}
            sentiment={sentiment}
            onSentimentChange={(s) => { setSentiment(s); setPage(1); }}
            sortBy={sortBy}
            onSortByChange={setSortBy}
            selectedAccount={selectedAccount}
            onAccountChange={(account) => { setSelectedAccount(account); setPage(1); }}
            accounts={accountsList}
          />
        </div>
      </div>

      {/* Scrollable Content Area */}
      <div
        id="feed-scroll-container"
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-6 scroll-smooth"
      >
        <div className="max-w-5xl mx-auto space-y-4">

          {/* New Tweets Banner */}
          {newTweetsCount > 0 && page === 1 && (
            <NewTweetsBanner
              count={newTweetsCount}
              onClick={loadNewTweets}
            />
          )}

          {/* Selected Tweets Action Bar */}
          {selectedTweets.size > 0 && (
            <div className={cn(
              "sticky top-0 z-10 flex items-center justify-between p-3 rounded-xl mb-4 shadow-lg backdrop-blur-md",
              "bg-primary/10 border border-primary/20"
            )}>
              <span className="text-sm text-text-secondary">
                {selectedTweets.size} tweet{selectedTweets.size > 1 ? "s" : ""} selected
              </span>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => setSelectedTweets(new Set())}>
                  Clear
                </Button>
                <Button variant="primary" size="sm">
                  Analyze Selected
                </Button>
              </div>
            </div>
          )}

          {/* Tweet List */}
          <Card className="overflow-hidden bg-transparent border-0 shadow-none">
            <CardContent className="p-0">
              {isLoading || searchLoading ? (
                <div className="flex flex-col items-center justify-center py-16 gap-3">
                  <Spinner size="lg" />
                  <span className="text-sm text-text-muted">Loading tweets...</span>
                </div>
              ) : displayTweets && displayTweets.length > 0 ? (
                <div className="divide-y divide-border">
                  {displayTweets.map((tweet: Tweet) => (
                    <TweetCard
                      key={tweet.id}
                      tweet={tweet}
                      selectable
                      selected={selectedTweets.has(tweet.id)}
                      onSelect={handleTweetSelect}
                    />
                  ))}
                </div>
              ) : (
                <div className="py-16 text-center">
                  <div className="text-4xl mb-3">📭</div>
                  <p className="text-text-muted">No tweets found</p>
                  <p className="text-sm text-text-muted mt-1">
                    Try adjusting your filters or add more accounts to track
                  </p>
                </div>
              )}

              {/* Load More / Infinite Scroll Trigger */}
              {tweetsData?.has_more && !searchQuery && (
                <div
                  ref={loadMoreRef}
                  className="p-6 border-t border-border"
                >
                  {isFetching ? (
                    <div className="flex items-center justify-center gap-3">
                      <Loader2 size={20} className="animate-spin text-primary" />
                      <span className="text-sm text-text-muted">Loading more...</span>
                    </div>
                  ) : (
                    <Button
                      variant="secondary"
                      className="w-full gap-2"
                      onClick={loadMore}
                    >
                      <ArrowDown size={16} />
                      Load More Tweets
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Footer Stats */}
          {tweetsData && (
            <div className="text-center text-xs text-text-muted py-4">
              Showing {displayTweets?.length || 0} of {tweetsData.total} tweets
              {isLive && (
                <span className="ml-2">
                  · Auto-refreshing every 30s
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
