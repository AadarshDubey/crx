"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Rss,
  MessageSquare,
  BarChart3,
  Users,
  Rocket,
  Zap
} from "lucide-react";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/feed", label: "Intel Feed", icon: Rss },
  { href: "/chat", label: "AI Oracle", icon: MessageSquare },
  { href: "/analytics", label: "Deep Analytics", icon: BarChart3 },
  { href: "/accounts", label: "Watchlist", icon: Users },
];

interface SidebarProps {
  className?: string;
  onClose?: () => void;
}

export function Sidebar({ className, onClose }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className={cn(
      "fixed left-0 top-0 z-40 h-screen w-64 bg-background/50 backdrop-blur-xl border-r border-white/5 transition-transform duration-300",
      className
    )}>
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-6 border-b border-white/5">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-accent shadow-[0_0_15px_rgba(0,255,136,0.3)] group cursor-pointer overflow-hidden">
            <div className="absolute inset-0 bg-white/20 group-hover:bg-transparent transition-colors" />
            <Rocket className="w-5 h-5 text-black z-10" />
          </div>
          <div>
            <h1 className="text-xl font-bold font-heading text-transparent bg-clip-text bg-gradient-to-r from-white to-white/70 tracking-tight">CRX Pipeline</h1>
            <p className="text-[10px] font-mono text-primary uppercase tracking-widest">Sentinel v2.0</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-8 space-y-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onClose}
                className={cn(
                  "relative flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-300 group overflow-hidden",
                  isActive
                    ? "text-primary bg-primary/10 shadow-[0_0_20px_rgba(0,255,136,0.1)]"
                    : "text-text-secondary hover:text-white hover:bg-white/5"
                )}
              >
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-primary rounded-r-full shadow-[0_0_10px_theme('colors.primary')]" />
                )}
                <Icon size={20} className={cn("transition-transform group-hover:scale-110", isActive && "text-primary")} />
                <span className="font-medium tracking-wide">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-6 py-6 border-t border-white/5">
          <div className="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-bullish/10 to-transparent border border-bullish/20">
            <div className="relative">
              <div className="w-2 h-2 rounded-full bg-bullish animate-pulse" />
              <div className="absolute inset-0 w-2 h-2 rounded-full bg-bullish animate-ping opacity-75" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-bold text-bullish tracking-wider">SYSTEM ONLINE</span>
              <span className="text-[10px] text-text-muted font-mono">Latency: 12ms</span>
            </div>
            <Zap className="ml-auto w-4 h-4 text-bullish opacity-50" />
          </div>
        </div>
      </div>
    </aside>
  );
}
