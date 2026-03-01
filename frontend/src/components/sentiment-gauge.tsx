"use client";

import { cn } from "@/lib/utils";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useRef } from "react";

interface SentimentGaugeProps {
  bullish: number;
  bearish: number;
  neutral?: number;
  className?: string;
}

export function SentimentGauge({
  bullish,
  bearish,
  neutral = 0,
  className,
}: SentimentGaugeProps) {
  // Normalize values
  const total = bullish + bearish + neutral;
  const normalizedBullish = total > 0 ? (bullish / total) * 100 : 33.33;
  const normalizedBearish = total > 0 ? (bearish / total) * 100 : 33.33;

  const gaugePosition = 50 + (normalizedBullish - normalizedBearish) / 2;
  const sentiment = normalizedBullish > normalizedBearish + 10 ? "bullish" : normalizedBearish > normalizedBullish + 10 ? "bearish" : "neutral";

  // 3D Tilt Effect
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  const mouseXSpring = useSpring(x);
  const mouseYSpring = useSpring(y);

  const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], ["17.5deg", "-17.5deg"]);
  const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], ["-17.5deg", "17.5deg"]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const xPct = mouseX / width - 0.5;
    const yPct = mouseY / height - 0.5;
    x.set(xPct);
    y.set(yPct);
  };

  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <motion.div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        rotateX,
        rotateY,
        transformStyle: "preserve-3d",
      }}
      className={cn("space-y-4 p-6 rounded-2xl bg-surface/40 border border-white/5 backdrop-blur-md shadow-glass", className)}
    >
      <h3 className="text-sm font-medium text-text-secondary uppercase tracking-wider mb-2">Market Sentiment</h3>

      {/* Gauge Bar */}
      <div className="relative h-6 bg-surface-highlight rounded-full overflow-hidden shadow-inner border border-white/5">
        <div className="absolute inset-0 bg-gradient-to-r from-bearish via-neutral to-bullish opacity-50" />

        {/* Indicator */}
        <motion.div
          initial={{ left: "50%" }}
          animate={{ left: `${gaugePosition}%` }}
          transition={{ type: "spring", stiffness: 200, damping: 20 }}
          className="absolute top-0 bottom-0 w-1 bg-white shadow-[0_0_15px_rgba(255,255,255,0.8)] z-10"
        />
      </div>

      {/* Labels */}
      <div className="flex justify-between text-xs font-mono text-text-muted px-1">
        <span className="text-bearish">BEARISH</span>
        <span className="text-neutral">NEUTRAL</span>
        <span className="text-bullish">BULLISH</span>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-3 gap-2 mt-4 text-center">
        <div className="p-2 rounded-lg bg-bearish/10 border border-bearish/20">
          <div className="text-xs text-bearish mb-1">Bearish</div>
          <div className="text-lg font-bold text-white">{bearish}%</div>
        </div>
        <div className="p-2 rounded-lg bg-neutral/10 border border-neutral/20">
          <div className="text-xs text-neutral mb-1">Neutral</div>
          <div className="text-lg font-bold text-white max-w-full overflow-hidden text-ellipsis">{Math.round(100 - bullish - bearish)}%</div>
        </div>
        <div className="p-2 rounded-lg bg-bullish/10 border border-bullish/20">
          <div className="text-xs text-bullish mb-1">Bullish</div>
          <div className="text-lg font-bold text-white">{bullish}%</div>
        </div>
      </div>
    </motion.div>
  );
}
