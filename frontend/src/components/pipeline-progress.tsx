"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Activity, CheckCircle2, AlertCircle, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PipelineState {
  status: "idle" | "running" | "completed" | "error";
  step: number;
  total_steps: number;
  label: string;
  detail: string;
  percentage: number;
  last_completed_at: string | null;
  stats: Record<string, any>;
}

const DEFAULT_STATE: PipelineState = {
  status: "idle",
  step: 0,
  total_steps: 6,
  label: "",
  detail: "",
  percentage: 0,
  last_completed_at: null,
  stats: {},
};

export function PipelineProgress() {
  const [state, setState] = useState<PipelineState>(DEFAULT_STATE);
  const [isConnected, setIsConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(`${API_BASE_URL}/api/pipeline/stream`);
    eventSourceRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
    };

    es.onmessage = (event) => {
      try {
        const data: PipelineState = JSON.parse(event.data);
        setState(data);
      } catch {
        // Ignore parse errors (heartbeats, etc.)
      }
    };

    es.onerror = () => {
      setIsConnected(false);
      es.close();

      // Reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };
  }, []);

  useEffect(() => {
    // Fetch initial status first
    fetch(`${API_BASE_URL}/api/pipeline/status`)
      .then((res) => res.json())
      .then((data) => setState(data))
      .catch(() => {});

    // Then connect SSE
    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const isActive = state.status === "running";
  const isCompleted = state.status === "completed";
  const isError = state.status === "error";
  const isIdle = state.status === "idle";

  // Format the last completed time
  const lastSyncText = state.last_completed_at
    ? formatRelativeTime(state.last_completed_at)
    : null;

  return (
    <div
      className={cn(
        "relative overflow-hidden transition-all duration-500 ease-out",
        isActive && "pipeline-active",
        isCompleted && "pipeline-completed"
      )}
    >
      {/* ─── Active Pipeline Bar ─── */}
      {(isActive || isCompleted) && (
        <div className="relative bg-surface/50 backdrop-blur-sm border border-white/5 rounded-lg mx-6 mt-4 overflow-hidden">
          {/* Ambient glow behind the bar */}
          <div
            className={cn(
              "absolute inset-0 opacity-20 transition-opacity duration-1000",
              isActive && "pipeline-glow",
              isCompleted && "opacity-10"
            )}
            style={{
              background: isCompleted
                ? "linear-gradient(90deg, rgba(16, 185, 129, 0.15), rgba(52, 211, 153, 0.05))"
                : "linear-gradient(90deg, rgba(16, 185, 129, 0.2), rgba(6, 182, 212, 0.1))",
            }}
          />

          <div className="relative px-4 py-3">
            {/* Top row: Status text + percentage */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2.5">
                {isActive && (
                  <Zap
                    size={14}
                    className="text-primary animate-pulse"
                    fill="currentColor"
                  />
                )}
                {isCompleted && (
                  <CheckCircle2 size={14} className="text-primary" />
                )}

                <span className="text-xs font-mono font-semibold tracking-widest uppercase text-primary">
                  {isActive
                    ? `Global Data Sync In Progress... ${state.percentage}%`
                    : "Sync Complete"}
                </span>
              </div>

              {isActive && (
                <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
                  {state.step}/{state.total_steps}
                </span>
              )}
            </div>

            {/* Progress bar track */}
            <div className="relative h-1.5 bg-white/5 rounded-full overflow-hidden">
              {/* Filled portion */}
              <div
                className={cn(
                  "absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out",
                  isCompleted
                    ? "bg-gradient-to-r from-primary/80 to-primary"
                    : "progress-bar-fill"
                )}
                style={{ width: `${state.percentage}%` }}
              />

              {/* Shine sweep effect (only when active) */}
              {isActive && (
                <div
                  className="absolute inset-y-0 left-0 rounded-full progress-bar-shine"
                  style={{ width: `${state.percentage}%` }}
                />
              )}
            </div>

            {/* Bottom row: Step label + detail */}
            {isActive && state.label && (
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[11px] font-medium text-text-secondary">
                  {state.label}
                </span>
                {state.detail && (
                  <>
                    <span className="text-text-muted text-[10px]">·</span>
                    <span className="text-[10px] text-text-muted font-mono truncate max-w-[300px]">
                      {state.detail}
                    </span>
                  </>
                )}
              </div>
            )}

            {/* Completed summary */}
            {isCompleted && state.detail && (
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[11px] text-text-muted">{state.detail}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─── Error State ─── */}
      {isError && (
        <div className="relative bg-bearish/5 border border-bearish/20 rounded-lg mx-6 mt-4 overflow-hidden">
          <div className="px-4 py-3 flex items-center gap-2.5">
            <AlertCircle size={14} className="text-bearish" />
            <span className="text-xs font-mono font-semibold tracking-widest uppercase text-bearish">
              Sync Error
            </span>
            {state.detail && (
              <span className="text-[10px] text-text-muted font-mono truncate ml-2">
                {state.detail}
              </span>
            )}
          </div>
        </div>
      )}

      {/* ─── Idle Indicator ─── */}
      {isIdle && (
        <div className="flex items-center gap-2 mx-6 mt-3">
          {lastSyncText && (
            <span className="text-[10px] text-text-muted font-mono">
              Last sync: {lastSyncText}
            </span>
          )}
          {!isConnected && (
            <span className="text-[10px] text-bearish font-mono">
              · Reconnecting...
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Formats a UTC ISO string as a relative time (e.g., "2 min ago").
 */
function formatRelativeTime(isoString: string): string {
  const now = new Date();
  const then = new Date(isoString + "Z"); // Ensure UTC
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;

  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;

  return `${Math.floor(diffHr / 24)}d ago`;
}
