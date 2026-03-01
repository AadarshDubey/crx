"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { TrendingUp, TrendingDown, Flame } from "lucide-react";
import { cn, formatNumber } from "@/lib/utils";

interface Coin {
  symbol: string;
  name?: string;
  current_price?: number;
  price_change_percentage_24h?: number;
  image?: string;
  market_cap_rank?: number;
}

interface TopCoinsProps {
  coins: Coin[];
  title?: string;
  showPrice?: boolean;
  showRank?: boolean;
  className?: string;
}

export function TopCoins({ 
  coins, 
  title = "Top Coins", 
  showPrice = true,
  showRank = true,
  className 
}: TopCoinsProps) {
  const formatPrice = (price: number) => {
    if (price >= 1000) {
      return `$${formatNumber(price)}`;
    } else if (price >= 1) {
      return `$${price.toFixed(2)}`;
    } else if (price >= 0.0001) {
      return `$${price.toFixed(4)}`;
    } else {
      return `$${price.toFixed(8)}`;
    }
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        {coins.length === 0 ? (
          <div className="p-4 text-center text-text-muted text-sm">
            Loading...
          </div>
        ) : (
          <div className="divide-y divide-border">
            {coins.map((coin, index) => {
              const change = coin.price_change_percentage_24h || 0;
              const isPositive = change > 0;
              const isNegative = change < 0;

              return (
                <div
                  key={coin.symbol}
                  className="flex items-center justify-between px-4 py-2.5 hover:bg-surface-light/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    {showRank && (
                      <span className="text-xs text-text-muted w-4">
                        {coin.market_cap_rank || index + 1}.
                      </span>
                    )}
                    {coin.image ? (
                      <img 
                        src={coin.image} 
                        alt={coin.symbol} 
                        className="w-6 h-6 rounded-full"
                      />
                    ) : (
                      <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center">
                        <span className="text-[10px] font-bold text-primary">
                          {coin.symbol[0]}
                        </span>
                      </div>
                    )}
                    <div>
                      <span className="font-medium text-text-primary text-sm">
                        ${coin.symbol}
                      </span>
                      {coin.name && (
                        <p className="text-xs text-text-muted truncate max-w-[80px]">
                          {coin.name}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end">
                    {showPrice && coin.current_price !== undefined && (
                      <span className="text-sm text-text-primary font-medium">
                        {formatPrice(coin.current_price)}
                      </span>
                    )}
                    <div
                      className={cn(
                        "flex items-center gap-1 text-xs font-medium",
                        isPositive && "text-bullish",
                        isNegative && "text-bearish",
                        !isPositive && !isNegative && "text-text-muted"
                      )}
                    >
                      {isPositive ? (
                        <TrendingUp size={12} />
                      ) : isNegative ? (
                        <TrendingDown size={12} />
                      ) : null}
                      {isPositive && "+"}
                      {change.toFixed(2)}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface MemecoinsSectionProps {
  coins: Coin[];
  className?: string;
}

export function MemecoinsSection({ coins, className }: MemecoinsSectionProps) {
  return (
    <TopCoins
      coins={coins}
      title="🔥 Trending Memecoins"
      showPrice={true}
      showRank={false}
      className={className}
    />
  );
}
