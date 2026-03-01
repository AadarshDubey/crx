"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface ActivityHeatmapData {
    day: string;
    hour: number;
    count: number;
    intensity: number;
}

interface ActivityHeatmapProps {
    data: ActivityHeatmapData[];
    title?: string;
    className?: string;
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const FULL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const HOURS = [0, 4, 8, 12, 16, 20];

export function ActivityHeatmap({
    data,
    title = "Tweet Activity Heatmap",
    className,
}: ActivityHeatmapProps) {
    const [hoveredCell, setHoveredCell] = useState<{ day: string; hour: number } | null>(null);
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

    // Get data for a specific cell
    const getCellData = (day: string, hour: number) => {
        return data.find((d) => d.day === day && d.hour === hour);
    };

    // Get background color based on intensity
    const getHeatmapColor = (intensity: number) => {
        if (intensity === 0) return "bg-surface-light/20 hover:bg-surface-light/40";
        if (intensity < 0.2) return "bg-emerald-900/40 hover:bg-emerald-900/60";
        if (intensity < 0.4) return "bg-emerald-700/50 hover:bg-emerald-700/70";
        if (intensity < 0.6) return "bg-emerald-500/60 hover:bg-emerald-500/80";
        if (intensity < 0.8) return "bg-emerald-400/70 hover:bg-emerald-400/90";
        return "bg-emerald-400 hover:bg-emerald-300";
    };

    // Get activity level text
    const getActivityLevel = (intensity: number) => {
        if (intensity === 0) return { text: "No Activity", color: "text-text-muted" };
        if (intensity < 0.25) return { text: "Low Activity", color: "text-emerald-600" };
        if (intensity < 0.5) return { text: "Moderate Activity", color: "text-emerald-500" };
        if (intensity < 0.75) return { text: "High Activity", color: "text-emerald-400" };
        return { text: "Peak Activity 🔥", color: "text-emerald-300" };
    };

    // Format hour range for display
    const formatHourRange = (hour: number) => {
        const formatHour = (h: number) => {
            if (h === 0) return "12 AM";
            if (h === 12) return "12 PM";
            if (h < 12) return `${h} AM`;
            return `${h - 12} PM`;
        };
        return `${formatHour(hour)} - ${formatHour((hour + 4) % 24)}`;
    };

    // Format hour for header
    const formatHourHeader = (hour: number) => {
        if (hour === 0) return "12 AM";
        if (hour === 12) return "12 PM";
        if (hour < 12) return `${hour} AM`;
        return `${hour - 12} PM`;
    };

    // Get insight message based on data
    const getInsight = (count: number, intensity: number, day: string, hour: number) => {
        if (count === 0) return "No tweets posted during this time";

        const timeContext = hour >= 8 && hour < 20 ? "business hours" : "off-hours";
        const dayContext = day === "Sat" || day === "Sun" ? "weekend" : "weekday";

        if (intensity >= 0.75) {
            return `🎯 Prime posting time! Influencers are most active here`;
        }
        if (intensity >= 0.5) {
            return `Good engagement window for ${dayContext} ${timeContext}`;
        }
        if (intensity >= 0.25) {
            return `Moderate activity - some influencers active`;
        }
        return `Quiet period - fewer influencers posting`;
    };

    // Handle mouse move for tooltip position
    const handleMouseMove = (e: React.MouseEvent, day: string, hour: number) => {
        const rect = e.currentTarget.getBoundingClientRect();
        setTooltipPosition({
            x: rect.left + rect.width / 2,
            y: rect.top - 10,
        });
        setHoveredCell({ day, hour });
    };

    // Calculate totals for context
    const totalTweets = data.reduce((sum, d) => sum + d.count, 0);
    const avgPerSlot = totalTweets / data.length || 0;
    const peakSlot = data.reduce((max, d) => d.count > max.count ? d : max, data[0]);

    return (
        <div className={cn("space-y-4 relative", className)}>
            {/* Stats bar */}
            <div className="flex justify-between items-center text-xs text-text-muted px-2 py-1 bg-surface-light/20 rounded-lg">
                <span>📊 Total: <span className="text-text-secondary font-medium">{totalTweets} tweets</span></span>
                <span>📈 Avg: <span className="text-text-secondary font-medium">{avgPerSlot.toFixed(1)}/slot</span></span>
                {peakSlot && (
                    <span>🔥 Peak: <span className="text-emerald-400 font-medium">{peakSlot.day} {formatHourHeader(peakSlot.hour)}</span></span>
                )}
            </div>

            {/* Hour labels header */}
            <div className="flex gap-1 pl-12">
                {HOURS.map((hour) => (
                    <div
                        key={hour}
                        className="flex-1 text-center text-[10px] text-text-muted font-mono uppercase tracking-wider"
                    >
                        {formatHourHeader(hour)}
                    </div>
                ))}
            </div>

            {/* Grid */}
            <div className="space-y-1">
                {DAYS.map((day, dayIndex) => (
                    <div key={day} className="flex items-center gap-2 group">
                        <div className="w-10 text-xs text-text-muted font-mono group-hover:text-primary transition-colors text-right">
                            {day}
                        </div>
                        <div className="flex-1 flex gap-1">
                            {HOURS.map((hour) => {
                                const cellData = getCellData(day, hour);
                                const intensity = cellData?.intensity ?? 0;
                                const count = cellData?.count ?? 0;
                                const isHovered = hoveredCell?.day === day && hoveredCell?.hour === hour;

                                return (
                                    <div
                                        key={hour}
                                        className={cn(
                                            "flex-1 h-10 rounded-md transition-all duration-200 cursor-pointer",
                                            "flex items-center justify-center relative",
                                            getHeatmapColor(intensity),
                                            "border border-white/5",
                                            isHovered && "ring-2 ring-white/50 scale-105 z-10"
                                        )}
                                        onMouseEnter={(e) => handleMouseMove(e, day, hour)}
                                        onMouseLeave={() => setHoveredCell(null)}
                                    >
                                        {/* Show count if there are tweets */}
                                        {count > 0 && (
                                            <span className={cn(
                                                "text-xs font-medium transition-opacity",
                                                intensity > 0.5 ? "text-black/70" : "text-white/70"
                                            )}>
                                                {count}
                                            </span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            {/* Tooltip */}
            {hoveredCell && (
                <div
                    className="fixed z-50 pointer-events-none"
                    style={{
                        left: tooltipPosition.x,
                        top: tooltipPosition.y,
                        transform: "translate(-50%, -100%)",
                    }}
                >
                    <div className="bg-surface border border-white/10 rounded-xl shadow-2xl p-4 min-w-[240px] backdrop-blur-xl">
                        {(() => {
                            const cellData = getCellData(hoveredCell.day, hoveredCell.hour);
                            const intensity = cellData?.intensity ?? 0;
                            const count = cellData?.count ?? 0;
                            const activityLevel = getActivityLevel(intensity);
                            const dayIndex = DAYS.indexOf(hoveredCell.day);

                            return (
                                <>
                                    {/* Header */}
                                    <div className="flex items-center justify-between mb-3">
                                        <div>
                                            <p className="font-semibold text-text-primary">
                                                {FULL_DAYS[dayIndex]}
                                            </p>
                                            <p className="text-xs text-text-muted">
                                                {formatHourRange(hoveredCell.hour)}
                                            </p>
                                        </div>
                                        <div className={cn(
                                            "px-2 py-1 rounded-full text-xs font-medium",
                                            intensity === 0 ? "bg-surface-light text-text-muted" :
                                                intensity < 0.5 ? "bg-emerald-900/50 text-emerald-400" :
                                                    "bg-emerald-500/30 text-emerald-300"
                                        )}>
                                            {activityLevel.text}
                                        </div>
                                    </div>

                                    {/* Stats */}
                                    <div className="grid grid-cols-2 gap-3 mb-3">
                                        <div className="bg-surface-light/30 rounded-lg p-2">
                                            <p className="text-2xl font-bold text-primary">{count}</p>
                                            <p className="text-[10px] text-text-muted uppercase tracking-wider">Tweets</p>
                                        </div>
                                        <div className="bg-surface-light/30 rounded-lg p-2">
                                            <p className="text-2xl font-bold text-text-primary">
                                                {intensity > 0 ? `${Math.round(intensity * 100)}%` : "—"}
                                            </p>
                                            <p className="text-[10px] text-text-muted uppercase tracking-wider">Intensity</p>
                                        </div>
                                    </div>

                                    {/* Insight */}
                                    <div className="text-xs text-text-secondary border-t border-white/5 pt-3">
                                        💡 {getInsight(count, intensity, hoveredCell.day, hoveredCell.hour)}
                                    </div>

                                    {/* Progress bar showing relative activity */}
                                    {count > 0 && (
                                        <div className="mt-3">
                                            <div className="flex justify-between text-[10px] text-text-muted mb-1">
                                                <span>Relative activity</span>
                                                <span>{Math.round(intensity * 100)}% of peak</span>
                                            </div>
                                            <div className="h-1.5 bg-surface-light rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full transition-all"
                                                    style={{ width: `${intensity * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                    )}
                                </>
                            );
                        })()}
                    </div>
                </div>
            )}

            {/* Legend */}
            <div className="flex justify-center items-center gap-4 mt-6 text-[10px] text-text-muted uppercase tracking-wider">
                <span className="text-text-secondary">Activity Level:</span>
                <div className="flex items-center gap-1">
                    <div className="w-4 h-4 rounded bg-surface-light/20 border border-white/5" />
                    <span>None</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-4 h-4 rounded bg-emerald-900/40 border border-white/5" />
                    <span>Low</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-4 h-4 rounded bg-emerald-500/60 border border-white/5" />
                    <span>Moderate</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className="w-4 h-4 rounded bg-emerald-400 border border-white/5" />
                    <span>Peak</span>
                </div>
            </div>
        </div>
    );
}
