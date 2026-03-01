"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { cn } from "@/lib/utils";

interface HeatmapData {
  day: string;
  hour: number;
  value: number;
  sentiment?: "bullish" | "bearish" | "neutral";
}

interface SentimentHeatmapProps {
  data: HeatmapData[];
  title?: string;
  className?: string;
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const HOURS = [0, 6, 12, 18];

export function SentimentHeatmap({
  data,
  title = "Sentiment Heatmap",
  className,
}: SentimentHeatmapProps) {
  // Create a grid of sentiment values
  const getHeatmapColor = (value: number) => {
    if (value > 0.3) return "bg-bullish";
    if (value < -0.3) return "bg-bearish";
    if (Math.abs(value) <= 0.1) return "bg-text-muted/30";
    return value > 0 ? "bg-bullish/50" : "bg-bearish/50";
  };

  const getValueForCell = (day: string, hour: number) => {
    const cell = data.find((d) => d.day === day && d.hour === hour);
    return cell?.value ?? 0;
  };

  return (
    <Card className={cn("bg-surface/30 backdrop-blur-sm border-white/5", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-wider text-text-muted">{title}</CardTitle>
        <p className="text-[10px] text-text-muted font-mono uppercase tracking-widest">Activity Pattern Analysis</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {/* Hour labels */}
          <div className="flex gap-1 pl-10">
            {HOURS.map((hour) => (
              <div
                key={hour}
                className="flex-1 text-center text-[10px] text-text-muted font-mono"
              >
                {hour}:00
              </div>
            ))}
          </div>

          {/* Grid */}
          {DAYS.map((day) => (
            <div key={day} className="flex items-center gap-1 group">
              <div className="w-8 text-[10px] text-text-muted font-mono group-hover:text-primary transition-colors">{day}</div>
              <div className="flex-1 flex gap-1">
                {[0, 3, 6, 9, 12, 15, 18, 21].map((hour) => {
                  const value = getValueForCell(day, hour);
                  return (
                    <div
                      key={hour}
                      className={cn(
                        "flex-1 h-6 rounded-sm transition-all duration-300 hover:scale-105 hover:shadow-[0_0_10px_rgba(255,255,255,0.2)]",
                        getHeatmapColor(value),
                        "border border-white/5"
                      )}
                      title={`${day} ${hour}:00 - ${(value * 100).toFixed(0)}%`}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="flex justify-center gap-6 mt-6 text-[10px] text-text-muted uppercase tracking-wider">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-bearish shadow-[0_0_5px_rgba(255,71,87,0.5)]" />
            <span>High Bearish</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-text-muted/30" />
            <span>Neutral</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-bullish shadow-[0_0_5px_rgba(0,255,136,0.5)]" />
            <span>High Bullish</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
