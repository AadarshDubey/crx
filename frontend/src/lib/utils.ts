import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

// Combine class names with tailwind merge
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format relative time (e.g., "5m ago", "2h ago")
export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return "Never";
  
  const d = typeof date === "string" ? new Date(date) : date;
  
  // Check if date is valid
  if (isNaN(d.getTime())) return "Unknown";
  
  return formatDistanceToNow(d, { addSuffix: true })
    .replace("about ", "")
    .replace(" minutes", "m")
    .replace(" minute", "m")
    .replace(" hours", "h")
    .replace(" hour", "h")
    .replace(" days", "d")
    .replace(" day", "d")
    .replace(" ago", " ago");
}

// Format number with K/M suffix
export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1).replace(/\.0$/, "") + "M";
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1).replace(/\.0$/, "") + "k";
  }
  return num.toString();
}

// Format price with proper decimals
export function formatPrice(price: number): string {
  if (price >= 1) {
    return price.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  return price.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 4,
    maximumFractionDigits: 6,
  });
}

// Format percentage
export function formatPercentage(value: number, includeSign = true): string {
  const sign = includeSign && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

// Get sentiment color class
export function getSentimentColor(
  sentiment: "bullish" | "bearish" | "neutral" | string
): string {
  switch (sentiment.toLowerCase()) {
    case "bullish":
      return "text-bullish";
    case "bearish":
      return "text-bearish";
    default:
      return "text-neutral";
  }
}

// Get sentiment background class
export function getSentimentBg(
  sentiment: "bullish" | "bearish" | "neutral" | string
): string {
  switch (sentiment.toLowerCase()) {
    case "bullish":
      return "bg-bullish/20 text-bullish";
    case "bearish":
      return "bg-bearish/20 text-bearish";
    default:
      return "bg-neutral/20 text-neutral";
  }
}

// Get sentiment dot color
export function getSentimentDot(
  sentiment: "bullish" | "bearish" | "neutral" | string
): string {
  switch (sentiment.toLowerCase()) {
    case "bullish":
      return "bg-bullish";
    case "bearish":
      return "bg-bearish";
    default:
      return "bg-neutral";
  }
}

// Extract coin symbols from text
export function extractCoins(text: string): string[] {
  const coinPattern = /\$([A-Z]{2,6})/g;
  const matches = text.match(coinPattern) || [];
  return Array.from(new Set(matches));
}

// Truncate text with ellipsis
export function truncate(text: string, length: number): string {
  if (text.length <= length) return text;
  return text.slice(0, length) + "...";
}

// Format date for display
export function formatDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return format(d, "MMM d, yyyy h:mm a");
}

// Generate unique ID
export function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

// Debounce function
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}
