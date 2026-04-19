"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type RoundIconButtonTone = "default" | "active";

export function RoundIconButton({
  tone = "default",
  as = "button",
  className,
  children,
  disabled = false,
  type = "button",
  title,
  ...props
}: Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  tone?: RoundIconButtonTone;
  as?: "button" | "span";
  className?: string;
  children: ReactNode;
  title?: string;
}) {
  const sharedClassName = cn(
    "inline-flex h-11 w-11 items-center justify-center rounded-full border shadow-sm transition",
    tone === "active"
      ? "border-slate-900 bg-slate-900 text-white"
      : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50",
    disabled && "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-300 shadow-none",
    className,
  );

  if (as === "span") {
    return (
      <span className={sharedClassName} title={title}>
        {children}
      </span>
    );
  }

  return (
    <button
      type={type}
      disabled={disabled}
      title={title}
      className={sharedClassName}
      {...props}
    >
      {children}
    </button>
  );
}
