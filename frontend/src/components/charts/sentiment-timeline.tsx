"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { cn } from "@/lib/utils";

interface SentimentTimelineProps {
  data: {
    timestamp: string;
    time_label?: string;
    bullish: number;
    bearish: number;
    neutral?: number;
    total_tweets?: number;
  }[];
  title?: string;
  className?: string;
}

export function SentimentTimeline({
  data,
  title = "Sentiment Timeline",
  className,
}: SentimentTimelineProps) {
  const formattedData = data.map((item) => ({
    ...item,
    time: item.time_label || new Date(item.timestamp).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    }),
  }));

  return (
    <Card className={cn("bg-surface/30 backdrop-blur-sm border-white/5", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-text-muted">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[250px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="bullishGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00ff88" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00ff88" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bearishGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ff4757" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ff4757" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis
                dataKey="time"
                stroke="#52525b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                dy={10}
              />
              <YAxis
                stroke="#52525b"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                dx={-10}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(10, 10, 10, 0.9)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "12px",
                  fontSize: "12px",
                  backdropFilter: "blur(10px)",
                  boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
                  color: "#fff"
                }}
                itemStyle={{ paddingBottom: 4 }}
              />
              <Area
                type="monotone"
                dataKey="bullish"
                stroke="#00ff88"
                fill="url(#bullishGradient)"
                strokeWidth={2}
                name="Bullish"
                animationDuration={1500}
              />
              <Area
                type="monotone"
                dataKey="bearish"
                stroke="#ff4757"
                fill="url(#bearishGradient)"
                strokeWidth={2}
                name="Bearish"
                animationDuration={1500}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
