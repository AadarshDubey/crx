import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#09090b", // Rich dark zinc
        surface: "#18181b", // Zinc 900
        "surface-highlight": "#27272a", // Zinc 800
        "surface-light": "#3f3f46", // Zinc 700
        border: "rgba(255, 255, 255, 0.08)",
        "border-light": "rgba(255, 255, 255, 0.15)",

        // Modern Professional Accents
        primary: "#10b981", // Emerald 500 (Smoother Bullish)
        secondary: "#8b5cf6", // Violet 500
        accent: "#06b6d4", // Cyan 500

        // Semantic
        bullish: "#10b981", // Emerald 500
        bearish: "#f43f5e", // Rose 500
        neutral: "#94a3b8", // Slate 400

        // Text
        "text-primary": "#f8fafc", // Slate 50
        "text-secondary": "#cbd5e1", // Slate 300
        "text-muted": "#64748b", // Slate 500
      },
      fontFamily: {
        sans: ["var(--font-lexend)", "system-ui", "sans-serif"],
        heading: ["var(--font-space-grotesk)", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      backgroundImage: {
        'gradient-bullish': 'linear-gradient(135deg, #10b981 0%, #34d399 100%)',
        'gradient-bearish': 'linear-gradient(135deg, #f43f5e 0%, #fb7185 100%)',
        'gradient-neutral': 'linear-gradient(135deg, #64748b 0%, #94a3b8 100%)',
        'gradient-glass': 'linear-gradient(145deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
        'gradient-glow': 'radial-gradient(circle at center, var(--tw-gradient-from) 0%, transparent 70%)',
      },
      boxShadow: {
        'glow-bullish': '0 0 15px rgba(16, 185, 129, 0.3)',
        'glow-bearish': '0 0 15px rgba(244, 63, 94, 0.3)',
        'glow-neutral': '0 0 15px rgba(148, 163, 184, 0.2)',
        'glass': '0 4px 20px 0 rgba(0, 0, 0, 0.25)',
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float": "float 3s ease-in-out infinite",
        "shimmer": "shimmer 2s linear infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-5px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
