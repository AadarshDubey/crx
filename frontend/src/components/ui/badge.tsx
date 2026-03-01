import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "bullish" | "bearish" | "neutral";
  size?: "sm" | "md";
  className?: string;
}

export function Badge({
  children,
  variant = "default",
  size = "sm",
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center font-medium rounded-full",
        {
          // Variants
          "bg-surface-light text-text-secondary": variant === "default",
          "bg-bullish/20 text-bullish": variant === "bullish",
          "bg-bearish/20 text-bearish": variant === "bearish",
          "bg-neutral/20 text-neutral": variant === "neutral",
          // Sizes
          "px-2 py-0.5 text-xs": size === "sm",
          "px-3 py-1 text-sm": size === "md",
        },
        className
      )}
    >
      {children}
    </span>
  );
}
