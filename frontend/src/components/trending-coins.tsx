"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { cn, formatNumber, formatPercentage } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";

interface TrendingCoin {
  symbol: string;
  price?: number;
  change: number;
}

interface TrendingCoinsProps {
  coins: TrendingCoin[];
  className?: string;
}

export function TrendingCoins({ coins, className }: TrendingCoinsProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">Trending Coins</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border">
          {coins.map((coin, index) => (
            <div
              key={coin.symbol}
              className="flex items-center justify-between px-4 py-3 hover:bg-surface-light/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-text-muted w-4">
                  {index + 1}.
                </span>
                <span className="font-semibold text-text-primary">
                  ${coin.symbol}
                </span>
              </div>
              <div
                className={cn(
                  "flex items-center gap-1 font-medium",
                  coin.change >= 0 ? "text-bullish" : "text-bearish"
                )}
              >
                {coin.change >= 0 ? (
                  <TrendingUp size={14} />
                ) : (
                  <TrendingDown size={14} />
                )}
                <span>{formatPercentage(coin.change)}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
