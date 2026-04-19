"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type SoftButtonTone = "neutral" | "accent";
type SoftButtonShape = "pill" | "surface";
type SoftButtonAlign = "center" | "left";

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
        "inline-flex items-center gap-2 border text-sm transition disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-50 disabled:text-slate-400",
        tone === "neutral" &&
          "border-slate-200 bg-white/85 text-slate-700 hover:border-slate-300 hover:bg-white hover:text-slate-900",
        tone === "accent" &&
          "border-[#e3c79d] bg-[#fff8ef] text-slate-800 hover:border-[#c49355] hover:bg-[#fff2df] hover:text-slate-900",
        shape === "pill" ? "rounded-full px-4 py-2.5" : "rounded-[24px] px-5 py-3.5",
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
