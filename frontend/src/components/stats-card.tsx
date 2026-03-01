"use client";

import { Card, CardContent } from "@/components/ui";
import { cn, formatNumber } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { motion } from "framer-motion";

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  className?: string;
  delay?: number;
}

export function StatsCard({
  title,
  value,
  subtitle,
  change,
  changeLabel,
  icon,
  className,
  delay = 0,
}: StatsCardProps) {
  const isPositive = change && change > 0;
  const isNegative = change && change < 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: delay * 0.1 }}
      whileHover={{ y: -5, boxShadow: "0 10px 30px -10px rgba(0, 255, 136, 0.2)" }}
      className={cn("h-full", className)}
    >
      <div className="relative overflow-hidden rounded-xl border border-white/5 bg-surface/40 backdrop-blur-md transition-colors hover:bg-surface/60 hover:border-primary/30 group h-full">

        {/* Neon Glow on Top */}
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

        <div className="p-6">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-sm font-medium text-text-secondary group-hover:text-primary/80 transition-colors uppercase tracking-wider">
              {title}
            </h3>
            {icon && (
              <div className="p-2 rounded-lg bg-surface-highlight/50 text-text-secondary group-hover:text-primary group-hover:bg-primary/10 transition-colors">
                {icon}
              </div>
            )}
          </div>

          <div className="space-y-1">
            <h2 className="text-3xl font-bold font-heading text-text-primary tracking-tight">
              {typeof value === "number" ? formatNumber(value) : value}
            </h2>

            {(change !== undefined || subtitle) && (
              <div className="flex items-center gap-2 mt-2">
                {change !== undefined && (
                  <div
                    className={cn(
                      "flex items-center gap-1 text-sm font-medium px-2 py-0.5 rounded-full border",
                      isPositive
                        ? "text-bullish border-bullish/20 bg-bullish/5"
                        : isNegative
                          ? "text-bearish border-bearish/20 bg-bearish/5"
                          : "text-text-muted border-white/5 bg-white/5"
                    )}
                  >
                    {isPositive ? (
                      <TrendingUp size={14} />
                    ) : isNegative ? (
                      <TrendingDown size={14} />
                    ) : (
                      <Minus size={14} />
                    )}
                    <span>
                      {isPositive ? "+" : ""}
                      {change}%
                    </span>
                  </div>
                )}
                {changeLabel && (
                  <span className="text-xs text-text-muted">{changeLabel}</span>
                )}
                {subtitle && (
                  <span className="text-xs text-text-muted">{subtitle}</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
