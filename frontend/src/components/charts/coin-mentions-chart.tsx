"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { cn } from "@/lib/utils";

interface CoinMentionsChartProps {
  data: {
    coin: string;
    count: number;
    percentage: number;
  }[];
  title?: string;
  className?: string;
}

const COLORS = [
  "#3b82f6", // Blue
  "#00ff88", // Bullish Green
  "#ff4757", // Bearish Red
  "#eab308", // Yellow
  "#a855f7", // Purple
  "#06b6d4", // Cyan
  "#f97316", // Orange
  "#ec4899", // Pink
];

export function CoinMentionsChart({
  data,
  title = "Trending Coins",
  className,
}: CoinMentionsChartProps) {
  const chartData = data.map((item) => ({
    name: item.coin,
    value: item.count,
    percentage: item.percentage,
  }));

  return (
    <Card className={cn("bg-surface/30 backdrop-blur-sm border-white/5", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-text-muted">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
                stroke="none"
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                    className="stroke-background stroke-2"
                  />
                ))}
              </Pie>
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
                formatter={(value: number, name: string) => [
                  `${value} mentions`,
                  name,
                ]}
              />
              <Legend
                formatter={(value) => (
                  <span className="text-text-secondary text-xs uppercase tracking-wide">{value}</span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
