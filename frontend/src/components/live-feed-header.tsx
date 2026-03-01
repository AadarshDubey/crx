"use client";

import { cn } from "@/lib/utils";
import { RefreshCw, Radio } from "lucide-react";
import { Button } from "@/components/ui";

interface LiveFeedHeaderProps {
    tweetCount: number;
    isLive?: boolean;
    onRefresh?: () => void;
    isRefreshing?: boolean;
}

export function LiveFeedHeader({
    tweetCount,
    isLive = true,
    onRefresh,
    isRefreshing = false,
}: LiveFeedHeaderProps) {
    return (
        <div className="sticky top-0 z-20 bg-background/95 backdrop-blur-sm border-b border-border">
            <div className="flex items-center justify-between px-6 py-4">
                <div className="flex items-center gap-4">
                    <h1 className="text-xl font-bold text-text-primary">Live Feed</h1>

                    {/* Tweet Count */}
                    <span className="text-sm text-text-muted">
                        {tweetCount.toLocaleString()} tweets
                    </span>

                    {/* Live Indicator */}
                    <div className="flex items-center gap-2">
                        <div className={cn(
                            "relative flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium",
                            isLive
                                ? "bg-bullish/20 text-bullish"
                                : "bg-text-muted/20 text-text-muted"
                        )}>
                            {/* Pulsing dot */}
                            <span className="relative flex h-2 w-2">
                                {isLive && (
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-bullish opacity-75"></span>
                                )}
                                <span className={cn(
                                    "relative inline-flex rounded-full h-2 w-2",
                                    isLive ? "bg-bullish" : "bg-text-muted"
                                )}></span>
                            </span>
                            <span>{isLive ? "Live" : "Offline"}</span>
                        </div>
                    </div>
                </div>

                {/* Refresh Button */}
                {onRefresh && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onRefresh}
                        disabled={isRefreshing}
                        className="gap-2"
                    >
                        <RefreshCw
                            size={16}
                            className={cn(isRefreshing && "animate-spin")}
                        />
                        Refresh
                    </Button>
                )}
            </div>
        </div>
    );
}
