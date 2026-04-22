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
        muted: "var(--color-muted)",
        app: "var(--bg-app)",
        canvas: "var(--bg-canvas)",
        surface: {
          primary: "var(--surface-primary)",
          secondary: "var(--surface-secondary)",
          elevated: "var(--surface-elevated)",
          lilac: "var(--surface-lilac)",
          rose: "var(--surface-rose)",
          mint: "var(--surface-mint)",
          sand: "var(--surface-sand)",
          ink: "var(--surface-ink)"
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
          inverse: "var(--text-inverse)"
        },
        border: {
          soft: "var(--border-soft)",
          strong: "var(--border-strong)",
          inverse: "var(--border-inverse)"
        },
        brand: {
          DEFAULT: "var(--accent-brand)",
          strong: "var(--accent-brand-strong)",
          blue: "var(--accent-blue)",
          rose: "var(--accent-rose)",
          mint: "var(--accent-mint)"
        }
      },
      fontFamily: {
        sans: ["var(--font-aa-stetica)"],
        mono: ["var(--font-aa-stetica)"],
        display: ["var(--font-aa-stetica)"]
      },
      boxShadow: {
        glass: "0 24px 80px rgba(15, 23, 42, 0.14)",
        "soft-sm": "var(--shadow-soft-sm)",
        "soft-md": "var(--shadow-soft-md)",
        "soft-xl": "var(--shadow-soft-xl)"
      },
      borderRadius: {
        panel: "var(--radius-panel)",
        control: "var(--radius-control)",
        pill: "var(--radius-pill)",
        bubble: "var(--radius-bubble)"
      },
      backgroundImage: {
        "hero-grid":
          "radial-gradient(circle at top, rgba(216, 180, 117, 0.28), transparent 35%), linear-gradient(135deg, rgba(255,255,255,0.65), rgba(255,255,255,0.08))",
        "soft-grid":
          "linear-gradient(rgba(24,24,27,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(24,24,27,0.035) 1px, transparent 1px)",
        "premium-canvas":
          "radial-gradient(circle at 12% 6%, rgba(208,164,109,0.22), transparent 32rem), radial-gradient(circle at 86% 10%, rgba(239,237,255,0.9), transparent 34rem), linear-gradient(180deg, var(--bg-canvas) 0%, var(--bg-app) 52%, #ebe7de 100%)"
      }
    }
  },
  plugins: []
};

export default config;
