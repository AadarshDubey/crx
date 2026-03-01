import { cn } from "@/lib/utils";
import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> { }

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", style, ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        className={cn(
          "w-full px-4 py-2 rounded-lg",
          "border border-border",
          "placeholder-text-muted",
          "focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent",
          "transition-colors",
          className
        )}
        style={{
          backgroundColor: "#252525",
          color: "#ffffff",
          ...style,
        }}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";
