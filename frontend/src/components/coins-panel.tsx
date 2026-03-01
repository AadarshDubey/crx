"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import Image from "next/image";

interface Coin {
  id: string;
  symbol: string;
  name: string;
  image: string;
  current_price: number;
  price_change_percentage_24h: number;
  market_cap_rank: number;
}

interface CoinsPanelProps {
  topCoins: Coin[];
  memecoins: Coin[];
}

function formatPrice(price: number): string {
  if (price >= 1000) {
    return `$${(price / 1000).toFixed(1)}k`;
  } else if (price >= 1) {
    return `$${price.toFixed(2)}`;
  } else if (price >= 0.0001) {
    return `$${price.toFixed(4)}`;
  } else {
    return `$${price.toFixed(8)}`;
  }
}

function CoinRow({ coin, rank }: { coin: Coin; rank: number }) {
  const isPositive = coin.price_change_percentage_24h >= 0;

  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-3">
        <span className="text-muted text-sm w-5">{rank}.</span>
        <div className="relative w-6 h-6 rounded-full overflow-hidden bg-card-hover">
          <Image
            src={coin.image}
            alt={coin.name}
            fill
            className="object-cover"
            unoptimized
          />
        </div>
        <div>
          <span className="font-medium text-sm">${coin.symbol.toUpperCase()}</span>
          <p className="text-xs text-muted">{coin.name}</p>
        </div>
      </div>
      <div className="text-right">
        <span className="font-medium text-sm">{formatPrice(coin.current_price)}</span>
        <p className={`text-xs flex items-center justify-end gap-1 ${isPositive ? "text-success" : "text-danger"}`}>
          <span>{isPositive ? "↗" : "↘"}</span>
          {isPositive ? "+" : ""}{coin.price_change_percentage_24h?.toFixed(2) || "0.00"}%
        </p>
      </div>
    </div>
  );
}

export function CoinsPanel({ topCoins, memecoins }: CoinsPanelProps) {
  const [activeTab, setActiveTab] = useState<"top" | "meme">("top");

  const coins = activeTab === "top" ? topCoins : memecoins;

  return (
    <Card className="bg-surface/30 backdrop-blur-md border-white/5 shadow-glass">
      <CardHeader className="pb-4 border-b border-white/5">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium uppercase tracking-wider text-text-muted">Market Pulse</CardTitle>
          <div className="flex bg-black/20 rounded-lg p-0.5 border border-white/5">
            <button
              onClick={() => setActiveTab("top")}
              className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all ${activeTab === "top"
                ? "bg-primary text-black shadow-lg shadow-primary/20"
                : "text-text-muted hover:text-white"
                }`}
            >
              Top 10
            </button>
            <button
              onClick={() => setActiveTab("meme")}
              className={`px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all ${activeTab === "meme"
                ? "bg-accent text-white shadow-lg shadow-accent/20"
                : "text-text-muted hover:text-white"
                }`}
            >
              🔥 DEGEN
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="max-h-[400px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-white/10 hover:scrollbar-thumb-white/20">
          {coins.length > 0 ? (
            coins.map((coin, index) => (
              <CoinRow key={coin.id} coin={coin} rank={index + 1} />
            ))
          ) : (
            <p className="text-muted text-sm text-center py-8 italic">No market data available</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
