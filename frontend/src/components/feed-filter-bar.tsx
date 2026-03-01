"use client";

import { useState, useCallback } from "react";
import { Input, Select, Badge, Button } from "@/components/ui";
import { Search, X, Filter, Clock, TrendingUp, User } from "lucide-react";
import { TimeRange, SortBy, FilterSentiment, TrackedAccount } from "@/types";
import { cn } from "@/lib/utils";

interface FeedFilterBarProps {
    searchQuery: string;
    onSearchChange: (query: string) => void;
    timeRange: TimeRange;
    onTimeRangeChange: (range: TimeRange) => void;
    sentiment: FilterSentiment;
    onSentimentChange: (sentiment: FilterSentiment) => void;
    sortBy: SortBy;
    onSortByChange: (sort: SortBy) => void;
    selectedAccount: string;
    onAccountChange: (account: string) => void;
    accounts: TrackedAccount[];
}

const timeRangeOptions = [
    { value: "1h", label: "1H" },
    { value: "24h", label: "24H" },
    { value: "7d", label: "7D" },
    { value: "30d", label: "30D" },
];

const sentimentOptions = [
    { value: "all", label: "All" },
    { value: "bullish", label: "Bullish" },
    { value: "bearish", label: "Bearish" },
];

export function FeedFilterBar({
    searchQuery,
    onSearchChange,
    timeRange,
    onTimeRangeChange,
    sentiment,
    onSentimentChange,
    sortBy,
    onSortByChange,
    selectedAccount,
    onAccountChange,
    accounts,
}: FeedFilterBarProps) {
    const hasActiveFilters =
        searchQuery ||
        timeRange !== "24h" ||
        sentiment !== "all" ||
        selectedAccount !== "";

    const clearFilters = useCallback(() => {
        onSearchChange("");
        onTimeRangeChange("24h");
        onSentimentChange("all");
        onAccountChange("");
        onSortByChange("latest");
    }, [onSearchChange, onTimeRangeChange, onSentimentChange, onAccountChange, onSortByChange]);

    return (
        <div className="bg-surface/30 backdrop-blur-md border border-white/5 rounded-2xl p-4 mb-6 shadow-glass">
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">

                {/* Search - Glass Input */}
                <div className="relative w-full md:w-auto md:flex-1 md:max-w-md group">
                    <Search
                        size={16}
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted group-hover:text-primary transition-colors"
                    />
                    <input
                        placeholder="Search intel..."
                        value={searchQuery}
                        onChange={(e) => onSearchChange(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-xl py-2.5 pl-10 pr-10 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary/50 focus:bg-white/10 transition-all font-sans"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => onSearchChange("")}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-white transition-colors"
                        >
                            <X size={14} />
                        </button>
                    )}
                </div>

                {/* Filters Row */}
                <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-2 md:pb-0 scrollbar-hide">
                    {/* Time Range Pills */}
                    <div className="flex bg-white/5 rounded-lg p-1 border border-white/5">
                        {timeRangeOptions.map((opt) => (
                            <button
                                key={opt.value}
                                onClick={() => onTimeRangeChange(opt.value as TimeRange)}
                                className={cn(
                                    "px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                                    timeRange === opt.value
                                        ? "bg-primary text-black shadow-lg shadow-primary/20"
                                        : "text-text-muted hover:text-white hover:bg-white/5"
                                )}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>

                    <div className="h-6 w-[1px] bg-white/10 mx-1" />

                    {/* Sentiment Dropdown (Styled) */}
                    <select
                        value={sentiment}
                        onChange={(e) => onSentimentChange(e.target.value as FilterSentiment)}
                        className="bg-white/5 border border-white/10 text-text-primary text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-primary/50 hover:bg-white/10 transition-colors cursor-pointer appearance-none"
                    >
                        <option value="all">All Sentiment</option>
                        <option value="bullish">🟢 Bullish</option>
                        <option value="bearish">🔴 Bearish</option>
                        <option value="neutral">⚪ Neutral</option>
                    </select>

                    {/* Sort Button */}
                    <button
                        onClick={() => onSortByChange(sortBy === 'latest' ? 'engagement' : 'latest')}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-xs text-text-secondary hover:text-white hover:border-primary/30 transition-all"
                    >
                        <TrendingUp size={14} />
                        <span className="hidden sm:inline">{sortBy === 'latest' ? 'Latest' : 'Popular'}</span>
                    </button>

                    {hasActiveFilters && (
                        <button
                            onClick={clearFilters}
                            className="ml-auto md:ml-2 p-2 text-text-muted hover:text-bearish transition-colors"
                            title="Clear filters"
                        >
                            <X size={16} />
                        </button>
                    )}
                </div>
            </div>

            {/* Active Filters Summary (if needed) */}
            {selectedAccount && (
                <div className="mt-3 flex items-center gap-2">
                    <span className="text-xs text-text-muted">Filtered by:</span>
                    <Badge variant="default" className="gap-1 bg-primary/10 text-primary border-primary/20">
                        @{selectedAccount}
                        <X size={12} className="cursor-pointer hover:text-white" onClick={() => onAccountChange("")} />
                    </Badge>
                </div>
            )}
        </div>
    );
}
