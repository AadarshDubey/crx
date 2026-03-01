"use client";

import { cn } from "@/lib/utils";
import { SelectHTMLAttributes, forwardRef } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: { value: string; label: string }[];
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, options, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          "px-4 py-2 rounded-lg",
          "border border-border",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent",
          "cursor-pointer transition-colors",
          "appearance-none bg-no-repeat bg-right pr-10",
          className
        )}
        style={{
          backgroundColor: "#252525",
          color: "#ffffff",
          backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
          backgroundPosition: "right 0.5rem center",
          backgroundSize: "1.5em 1.5em",
        }}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value} className="text-black bg-white">
            {option.label}
          </option>
        ))}
      </select>
    );
  }
);

Select.displayName = "Select";
