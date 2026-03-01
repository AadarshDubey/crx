"use client";

import { memo } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent, Badge } from "@/components/ui";
import { SentimentIndicator } from "@/components/sentiment-indicator";
import { cn, formatRelativeTime, formatNumber, extractCoins } from "@/lib/utils";
import { Tweet } from "@/types";
import { Heart, MessageCircle, Repeat, ExternalLink, Square, CheckSquare, Sparkles } from "lucide-react";

interface TweetCardProps {
  tweet: Tweet;
  compact?: boolean;
  className?: string;
  selectable?: boolean;
  selected?: boolean;
  onSelect?: (id: string, selected: boolean) => void;
  index?: number;
}

export const TweetCard = memo(function TweetCard({
  tweet,
  compact = false,
  className,
  selectable = false,
  selected = false,
  onSelect,
  index = 0,
}: TweetCardProps) {
  // Handle both nested and flat structures
  const authorHandle = tweet.author?.handle || tweet.author_handle || "unknown";
  const authorName = tweet.author?.name || tweet.author_name || authorHandle;
  const likes = tweet.engagement?.likes ?? tweet.likes ?? 0;
  const retweets = tweet.engagement?.retweets ?? tweet.retweets ?? 0;
  const replies = tweet.engagement?.replies ?? tweet.replies ?? 0;

  // Normalize sentiment - map positive/negative to bullish/bearish
  const rawSentiment = tweet.sentiment?.label || "neutral";
  const sentiment = rawSentiment === "positive" ? "bullish"
    : rawSentiment === "negative" ? "bearish"
      : rawSentiment as "bullish" | "bearish" | "neutral";

  const score = tweet.sentiment?.score || 0;

  const coins = tweet.topics || tweet.mentioned_coins || extractCoins(tweet.content);

  // Get sentiment display props
  const sentimentConfig = {
    bullish: {
      color: "text-bullish",
      bg: "bg-bullish/10 border-bullish/20",
      icon: "⚡",
      label: "BULLISH",
      glow: "shadow-[0_0_15px_rgba(16,185,129,0.15)] group-hover:shadow-[0_0_25px_rgba(16,185,129,0.3)]"
    },
    bearish: {
      color: "text-bearish",
      bg: "bg-bearish/10 border-bearish/20",
      icon: "🔻",
      label: "BEARISH",
      glow: "shadow-[0_0_15px_rgba(244,63,94,0.15)] group-hover:shadow-[0_0_25px_rgba(244,63,94,0.3)]"
    },
    neutral: {
      color: "text-neutral",
      bg: "bg-neutral/10 border-neutral/20",
      icon: "➖",
      label: "NEUTRAL",
      glow: ""
    },
  };

  const sentimentStyle = sentimentConfig[sentiment] || sentimentConfig.neutral;

  return (
    <div
      className={cn(
        "group relative p-5 border-b border-white/5",
        "transition-colors duration-150 ease-out",
        "hover:bg-white/[0.03]",
        "will-change-transform",
        selected && "bg-primary/5 border-l-2 border-l-primary",
        className
      )}
    >

      {/* Selection Checkbox + Header Row */}
      <div className="flex items-start gap-4 relative z-10">
        {/* Checkbox */}
        {selectable && (
          <button
            onClick={() => onSelect?.(tweet.id, !selected)}
            className={cn(
              "mt-1 p-0.5 rounded transition-colors",
              selected ? "text-primary" : "text-text-muted hover:text-text-secondary"
            )}
          >
            {selected ? <CheckSquare size={18} /> : <Square size={18} />}
          </button>
        )}

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-3 flex-wrap">
              {/* Avatar */}
              <div className="relative w-10 h-10 rounded-xl bg-surface-highlight overflow-hidden flex items-center justify-center flex-shrink-0 border border-white/10 group-hover:border-primary/50 transition-colors">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/20 to-accent/20 opacity-50" />
                <span className="relative text-sm font-bold text-primary font-mono">
                  {authorHandle[0]?.toUpperCase()}
                </span>
              </div>

              {/* Author Info */}
              <div className="flex flex-col">
                <span className="font-bold text-text-primary text-sm hover:text-primary cursor-pointer transition-colors tracking-wide">
                  @{authorHandle}
                </span>
                <span className="text-text-muted text-xs font-mono">
                  {formatRelativeTime(tweet.created_at)}
                </span>
              </div>
            </div>

            {/* Sentiment Badge */}
            <div className={cn(
              "flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-bold tracking-wider uppercase border backdrop-blur-sm transition-all duration-300",
              sentimentStyle.bg,
              sentimentStyle.color,
              sentimentStyle.glow
            )}>
              <span>{sentimentStyle.icon}</span>
              <span>{sentimentStyle.label}</span>
              {score > 0 && <span className="opacity-70 ml-1">{(score * 100).toFixed(0)}%</span>}
            </div>
          </div>

          {/* Content */}
          <div className="mt-3">
            <div className="flex items-start gap-2">
              {score > 0.9 && (
                <Sparkles size={14} className="text-accent mt-1 flex-shrink-0 animate-pulse" />
              )}
              <p
                className={cn(
                  "text-text-primary/90 leading-relaxed font-light",
                  compact ? "text-sm line-clamp-2" : "text-[15px]"
                )}
              >
                {tweet.content}
              </p>
            </div>
          </div>

          {/* Coin Tags */}
          {Array.isArray(coins) && coins.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {coins.slice(0, 5).map((coin) => (
                <span
                  key={coin}
                  className={cn(
                    "inline-flex items-center px-2.5 py-1 rounded-md text-[10px] font-bold font-mono tracking-wider",
                    "bg-white/5 text-primary border border-white/10",
                    "hover:border-primary/50 hover:bg-primary/10 transition-colors cursor-pointer"
                  )}
                >
                  ${coin.toUpperCase()}
                </span>
              ))}
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between mt-4">
            {/* Engagement Stats */}
            <div className="flex items-center gap-6 text-text-muted">
              <div className="flex items-center gap-2 text-xs group/stat hover:text-primary transition-colors cursor-pointer">
                <MessageCircle size={14} className="group-hover/stat:scale-110 transition-transform" />
                <span className="font-mono">{formatNumber(replies)}</span>
              </div>
              <div className="flex items-center gap-2 text-xs group/stat hover:text-bullish transition-colors cursor-pointer">
                <Repeat size={14} className="group-hover/stat:scale-110 transition-transform" />
                <span className="font-mono">{formatNumber(retweets)}</span>
              </div>
              <div className="flex items-center gap-2 text-xs group/stat hover:text-bearish transition-colors cursor-pointer">
                <Heart size={14} className="group-hover/stat:scale-110 transition-transform" />
                <span className="font-mono">{formatNumber(likes)}</span>
              </div>
            </div>

            {/* Open in X Link */}
            {tweet.url && (
              <a
                href={tweet.url}
                target="_blank"
                rel="noopener noreferrer"
                className={cn(
                  "flex items-center gap-1.5 text-xs font-medium text-text-muted",
                  "hover:text-primary transition-colors group/link px-3 py-1.5 rounded-lg hover:bg-white/5"
                )}
              >
                <span className="opacity-0 -translate-x-2 group-hover/link:opacity-100 group-hover/link:translate-x-0 transition-all duration-300">
                  Open
                </span>
                <ExternalLink size={12} className="group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
});

interface RecentTweetsProps {
  tweets: Tweet[];
  title?: string;
  className?: string;
}

export function RecentTweets({
  tweets,
  title = "Recent Tweets",
  className,
}: RecentTweetsProps) {
  return (
    <Card className={cn("bg-surface/30 backdrop-blur-md border-white/5 shadow-glass", className)}>
      <CardHeader className="flex flex-row items-center justify-between border-b border-white/5 pb-4">
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-text-muted">{title}</CardTitle>
        <Link
          href="/feed"
          className="text-xs font-mono text-primary hover:text-primary-hover transition-colors flex items-center gap-1 group"
        >
          VIEW ALL
          <ExternalLink size={10} className="group-hover:translate-x-0.5 transition-transform" />
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {tweets.length === 0 ? (
          <div className="p-8 text-center text-text-muted text-sm italic">
            No updates received yet...
          </div>
        ) : (
          tweets.map((tweet, i) => (
            <TweetCard key={tweet.id} tweet={tweet} compact index={i} />
          ))
        )}
      </CardContent>
    </Card>
  );
}
