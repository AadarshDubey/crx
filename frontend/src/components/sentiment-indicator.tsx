import { cn, getSentimentDot } from "@/lib/utils";

type SentimentType = "bullish" | "bearish" | "neutral" | "positive" | "negative";

interface SentimentIndicatorProps {
  sentiment: SentimentType;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

// Normalize sentiment labels
function normalizeSentiment(sentiment: SentimentType): "bullish" | "bearish" | "neutral" {
  if (sentiment === "positive") return "bullish";
  if (sentiment === "negative") return "bearish";
  if (sentiment === "bullish" || sentiment === "bearish") return sentiment;
  return "neutral";
}

export function SentimentIndicator({
  sentiment,
  showLabel = true,
  size = "md",
  className,
}: SentimentIndicatorProps) {
  const normalized = normalizeSentiment(sentiment);
  
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      <span
        className={cn(
          "rounded-full",
          getSentimentDot(normalized),
          {
            "h-2 w-2": size === "sm",
            "h-2.5 w-2.5": size === "md",
            "h-3 w-3": size === "lg",
          }
        )}
      />
      {showLabel && (
        <span
          className={cn(
            "capitalize font-medium",
            {
              "text-xs": size === "sm",
              "text-sm": size === "md",
              "text-base": size === "lg",
            },
            {
              "text-bullish": normalized === "bullish",
              "text-bearish": normalized === "bearish",
              "text-neutral": normalized === "neutral",
            }
          )}
        >
          {normalized}
        </span>
      )}
    </div>
  );
}
