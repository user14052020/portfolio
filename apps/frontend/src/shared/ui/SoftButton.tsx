"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type SoftButtonTone = "primary" | "neutral" | "subtle" | "accent" | "dark";
type SoftButtonShape = "pill" | "surface" | "compact";
type SoftButtonAlign = "center" | "left";

const toneClasses: Record<SoftButtonTone, string> = {
  primary:
    "border-[var(--accent-brand)] bg-[var(--accent-brand)] text-white shadow-[var(--shadow-soft-sm)] hover:border-[var(--accent-brand-strong)] hover:bg-[var(--accent-brand-strong)]",
  neutral:
    "border-[var(--border-soft)] bg-white/90 text-[var(--text-secondary)] shadow-[var(--shadow-soft-sm)] hover:border-[var(--border-strong)] hover:bg-white hover:text-[var(--text-primary)]",
  subtle:
    "border-transparent bg-[var(--surface-secondary)] text-[var(--text-secondary)] hover:bg-white/90 hover:text-[var(--text-primary)]",
  accent:
    "border-[#e8d0aa] bg-[#fff8ef] text-[#7f5424] shadow-[var(--shadow-soft-sm)] hover:border-[#c49355] hover:bg-[#fff2df] hover:text-[#4d3214]",
  dark:
    "border-[var(--surface-ink)] bg-[var(--surface-ink)] text-white shadow-[var(--shadow-soft-md)] hover:border-black hover:bg-black",
};

const shapeClasses: Record<SoftButtonShape, string> = {
  pill: "rounded-[var(--radius-pill)] px-4 py-2.5",
  surface: "rounded-[var(--radius-bubble)] px-5 py-3.5",
  compact: "rounded-[var(--radius-pill)] px-3 py-1.5 text-xs",
};

export function SoftButton({
  tone = "neutral",
  shape = "pill",
  align = "center",
  fullWidth = false,
  className,
  children,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  tone?: SoftButtonTone;
  shape?: SoftButtonShape;
  align?: SoftButtonAlign;
  fullWidth?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center gap-2 border text-sm font-medium transition duration-200 active:scale-[0.985] disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-400 disabled:shadow-none disabled:active:scale-100",
        toneClasses[tone],
        shapeClasses[shape],
        align === "left" ? "justify-start text-left" : "justify-center text-center",
        fullWidth && "w-full",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
