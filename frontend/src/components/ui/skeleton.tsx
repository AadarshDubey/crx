"use client";

import { cn } from "@/lib/utils";

interface SkeletonProps {
    className?: string;
    variant?: "line" | "circle" | "card";
    width?: string;
    height?: string;
}

export function Skeleton({
    className,
    variant = "line",
    width,
    height,
}: SkeletonProps) {
    const baseClasses =
        "animate-pulse bg-gradient-to-r from-white/5 via-white/10 to-white/5 bg-[length:200%_100%]";

    const variantClasses = {
        line: "rounded-md",
        circle: "rounded-full",
        card: "rounded-xl",
    };

    return (
        <div
            className={cn(baseClasses, variantClasses[variant], className)}
            style={{
                width: width,
                height: height,
                animation: "pulse 1.5s ease-in-out infinite, shimmer 2s ease-in-out infinite",
            }}
        />
    );
}

// ── Pre-built skeleton layouts for common patterns ──────────────

export function SkeletonStatsCard() {
    return (
        <div className="bg-surface/30 backdrop-blur-md border border-white/5 rounded-xl p-6 space-y-3">
            <div className="flex items-center justify-between">
                <Skeleton className="h-3 w-20" />
                <Skeleton variant="circle" className="h-8 w-8" />
            </div>
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-3 w-32" />
        </div>
    );
}

export function SkeletonArticleCard() {
    return (
        <div className="p-3 rounded-lg bg-card-hover/30 space-y-2">
            <div className="flex items-start gap-3">
                <Skeleton className="w-1 h-16 rounded-full" />
                <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                        <Skeleton className="h-4 w-16 rounded-full" />
                        <Skeleton className="h-4 w-12 rounded-full" />
                    </div>
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                    <div className="flex items-center gap-2 mt-1">
                        <Skeleton variant="circle" className="h-3 w-3" />
                        <Skeleton className="h-3 w-20" />
                    </div>
                </div>
            </div>
        </div>
    );
}

export function SkeletonCoinRow() {
    return (
        <div className="flex items-center gap-3 p-2">
            <Skeleton variant="circle" className="h-8 w-8" />
            <div className="flex-1 space-y-1">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-3 w-12" />
            </div>
            <div className="text-right space-y-1">
                <Skeleton className="h-4 w-16 ml-auto" />
                <Skeleton className="h-3 w-12 ml-auto" />
            </div>
        </div>
    );
}

export function SkeletonTweetCard() {
    return (
        <div className="p-4 rounded-lg bg-card-hover/30 space-y-3">
            <div className="flex items-center gap-3">
                <Skeleton variant="circle" className="h-10 w-10" />
                <div className="space-y-1">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-16" />
                </div>
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <div className="flex items-center gap-4 pt-1">
                <Skeleton className="h-3 w-10" />
                <Skeleton className="h-3 w-10" />
                <Skeleton className="h-3 w-10" />
            </div>
        </div>
    );
}

// ── Composite skeleton layouts for page sections ────────────────

export function SkeletonArticlesSection() {
    return (
        <div className="bg-surface/30 backdrop-blur-md border border-white/5 rounded-xl overflow-hidden shadow-glass">
            <div className="p-6 pb-4 border-b border-white/5">
                <Skeleton className="h-4 w-28" />
            </div>
            <div className="p-6 space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                    <SkeletonArticleCard key={i} />
                ))}
            </div>
        </div>
    );
}

export function SkeletonCoinsSection() {
    return (
        <div className="bg-surface/30 backdrop-blur-md border border-white/5 rounded-xl overflow-hidden shadow-glass">
            <div className="p-6 pb-4 border-b border-white/5">
                <Skeleton className="h-4 w-28" />
            </div>
            <div className="p-4 space-y-1">
                {Array.from({ length: 6 }).map((_, i) => (
                    <SkeletonCoinRow key={i} />
                ))}
            </div>
        </div>
    );
}

export function SkeletonTweetsSection() {
    return (
        <div className="bg-surface/30 backdrop-blur-md border border-white/5 rounded-xl overflow-hidden shadow-glass">
            <div className="p-6 pb-4 border-b border-white/5">
                <Skeleton className="h-4 w-36" />
            </div>
            <div className="p-4 space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                    <SkeletonTweetCard key={i} />
                ))}
            </div>
        </div>
    );
}
