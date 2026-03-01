"use client";

import { useState, useEffect } from "react";
import { Bell, RefreshCw, Menu, X } from "lucide-react";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";
import { Sidebar } from "./sidebar";

interface HeaderProps {
  title: string;
  subtitle?: string;
  showRefresh?: boolean;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  notificationCount?: number;
  onNotificationClick?: () => void;
  children?: React.ReactNode;
}

export function Header({
  title,
  subtitle,
  showRefresh = true,
  onRefresh,
  isRefreshing = false,
  notificationCount = 0,
  onNotificationClick,
  children,
}: HeaderProps) {
  const [currentTime, setCurrentTime] = useState<Date>(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="sticky top-0 z-30 bg-background/50 backdrop-blur-xl border-b border-white/5 shadow-sm">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-4">
          {/* Mobile Menu Trigger */}
          <div className="lg:hidden">
            <MobileNav />
          </div>

          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl md:text-2xl font-bold text-text-primary truncate max-w-[200px] md:max-w-none">{title}</h1>
              <span className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-bullish/20 text-bullish text-xs font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-bullish animate-pulse" />
                Live
              </span>
            </div>
            {subtitle && (
              <p className="text-xs md:text-sm text-text-muted mt-0.5 hidden md:block">{subtitle}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          {children}

          {/* Last updated */}
          <span className="text-xs text-text-muted hidden md:inline">
            Updated:{" "}
            {currentTime.toLocaleTimeString("en-US", {
              hour: "numeric",
              minute: "2-digit",
            })}
          </span>

          {/* Refresh button */}
          {showRefresh && onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isRefreshing}
              className="gap-2 hidden md:flex"
            >
              <RefreshCw
                size={16}
                className={cn(isRefreshing && "animate-spin")}
              />
              Refresh
            </Button>
          )}

          {/* Notifications */}
          <button
            onClick={onNotificationClick}
            className="relative p-2 rounded-lg hover:bg-surface-light transition-colors"
          >
            <Bell size={20} className={cn("text-text-secondary", notificationCount > 0 && "text-primary")} />
            {notificationCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 rounded-full bg-primary text-white text-xs font-medium">
                {notificationCount > 99 ? "99+" : notificationCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}

function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);

  // Lock body scroll when menu is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="p-2 -ml-2 text-text-muted hover:text-text-primary transition-colors"
      >
        <Menu size={24} />
      </button>

      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/80 backdrop-blur-sm z-50 transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={() => setIsOpen(false)}
      />

      {/* Sidebar Container */}
      <div
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-background shadow-2xl transition-transform duration-300 ease-out transform",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <Sidebar className="w-full h-full border-none" onClose={() => setIsOpen(false)} />
        <button
          onClick={() => setIsOpen(false)}
          className="absolute top-4 right-4 p-2 text-text-muted hover:text-white transition-colors lg:hidden"
        >
          <X size={20} />
        </button>
      </div>
    </>
  );
}
