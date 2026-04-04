import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/entities/**/*.{ts,tsx}",
    "./src/features/**/*.{ts,tsx}",
    "./src/shared/**/*.{ts,tsx}",
    "./src/widgets/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--color-background)",
        panel: "var(--color-panel)",
        accent: "var(--color-accent)",
        sand: "var(--color-sand)",
        ink: "var(--color-ink)",
        muted: "var(--color-muted)"
      },
      fontFamily: {
        sans: ["var(--font-aa-stetica)"],
        mono: ["var(--font-aa-stetica)"],
        display: ["var(--font-aa-stetica)"]
      },
      boxShadow: {
        glass: "0 24px 80px rgba(15, 23, 42, 0.14)"
      },
      backgroundImage: {
        "hero-grid":
          "radial-gradient(circle at top, rgba(216, 180, 117, 0.28), transparent 35%), linear-gradient(135deg, rgba(255,255,255,0.65), rgba(255,255,255,0.08))"
      }
    }
  },
  plugins: []
};

export default config;
