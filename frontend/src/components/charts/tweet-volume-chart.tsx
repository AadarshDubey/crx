"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { cn } from "@/lib/utils";

interface TweetVolumeChartProps {
  data: {
    date: string;
    count: number;
  }[];
  title?: string;
  className?: string;
}

export function TweetVolumeChart({
  data,
  title = "Tweet Volume",
  className,
}: TweetVolumeChartProps) {
  const formattedData = data.map((item) => ({
    ...item,
    day: new Date(item.date).toLocaleDateString("en-US", {
      weekday: "short",
    }),
  }));

  return (
    <Card className={cn("bg-surface/30 backdrop-blur-sm border-white/5", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-text-muted">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[250px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={formattedData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis
                dataKey="day"
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
                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                contentStyle={{
                  backgroundColor: "rgba(10, 10, 10, 0.9)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "12px",
                  fontSize: "12px",
                  backdropFilter: "blur(10px)",
                  boxShadow: "0 10px 30px rgba(0,0,0,0.5)",
                  color: "#fff"
                }}
              />
              <Bar
                dataKey="count"
                fill="#3b82f6"
                radius={[4, 4, 0, 0]}
                name="Tweets"
                animationDuration={1500}
              >
                {formattedData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill="url(#blueGradient)" />
                ))}
              </Bar>
              <defs>
                <linearGradient id="blueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={1} />
                  <stop offset="100%" stopColor="#2563eb" stopOpacity={0.6} />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
