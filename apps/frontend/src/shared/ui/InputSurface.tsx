"use client";

import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

export function InputSurface({
  children,
  className,
  disabled = false,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  disabled?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-[28px] border border-slate-200 bg-white/95 shadow-[0_18px_40px_rgba(15,23,42,0.06)] transition",
        disabled && "bg-slate-50 text-slate-400 shadow-none",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
