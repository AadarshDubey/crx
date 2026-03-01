"use client";

import { cn } from "@/lib/utils";
import { Bell, ChevronDown, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface NewTweetsBannerProps {
    count: number;
    onClick: () => void;
    className?: string;
}

export function NewTweetsBanner({ count, onClick, className }: NewTweetsBannerProps) {
    if (count <= 0) return null;

    return (
        <motion.button
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            onClick={onClick}
            className={cn(
                "relative w-full py-4 px-4 rounded-xl overflow-hidden",
                "bg-primary/10 backdrop-blur-md",
                "border border-primary/30",
                "flex items-center justify-center gap-3",
                "hover:bg-primary/20",
                "transition-all duration-300 ease-out",
                "group cursor-pointer",
                className
            )}
        >
            {/* Animated Background Mesh */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />

            {/* Content */}
            <div className="relative flex items-center gap-2">
                <div className="relative">
                    <Bell size={18} className="text-primary animate-bounce-slow" />
                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-primary rounded-full animate-ping" />
                    <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-primary rounded-full shadow-[0_0_10px_theme('colors.primary')]" />
                </div>

                <span className="font-bold text-text-primary tracking-wide">
                    {count} New Updates
                </span>

                <Sparkles size={14} className="text-accent animate-pulse" />
            </div>

            <ChevronDown
                size={16}
                className="text-primary/70 group-hover:translate-y-1 transition-transform ml-2"
            />
        </motion.button>
    );
}
