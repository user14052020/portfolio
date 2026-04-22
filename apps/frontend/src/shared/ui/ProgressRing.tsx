"use client";

import type { ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

type ProgressRingTone = "light" | "dark" | "brand";

const toneColors: Record<ProgressRingTone, { track: string; progress: string }> = {
  light: {
    track: "rgba(15,23,42,0.12)",
    progress: "var(--surface-ink)",
  },
  dark: {
    track: "rgba(255,255,255,0.18)",
    progress: "#ffffff",
  },
  brand: {
    track: "rgba(208,164,109,0.22)",
    progress: "var(--accent-brand-strong)",
  },
};

export function ProgressRing({
  size = 40,
  strokeWidth = 3,
  progress,
  tone = "light",
  trackColor,
  progressColor,
  className,
  label,
  labelClassName,
  ariaLabel,
  animated = true,
}: {
  size?: number;
  strokeWidth?: number;
  progress: number;
  tone?: ProgressRingTone;
  trackColor?: string;
  progressColor?: string;
  className?: string;
  label?: ReactNode;
  labelClassName?: string;
  ariaLabel?: string;
  animated?: boolean;
}) {
  const normalizedProgress = Math.min(Math.max(progress, 0), 1);
  const radius = (size - strokeWidth * 2) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - normalizedProgress);
  const resolvedTrackColor = trackColor ?? toneColors[tone].track;
  const resolvedProgressColor = progressColor ?? toneColors[tone].progress;

  const ring = (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      aria-hidden={ariaLabel ? undefined : true}
      aria-label={ariaLabel}
      role={ariaLabel ? "img" : undefined}
    >
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={resolvedTrackColor}
        strokeWidth={strokeWidth}
      />
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={resolvedProgressColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        className={animated ? "transition-[stroke-dashoffset] duration-500 ease-out" : undefined}
      />
    </svg>
  );

  if (!label) {
    return ring;
  }

  return (
    <span className={cn("relative inline-flex items-center justify-center", className)} style={{ height: size, width: size }}>
      <ProgressRing
        size={size}
        strokeWidth={strokeWidth}
        progress={normalizedProgress}
        tone={tone}
        trackColor={trackColor}
        progressColor={progressColor}
        animated={animated}
        className="absolute inset-0 h-full w-full -rotate-90"
      />
      <span className={cn("relative text-[11px] font-semibold tabular-nums", labelClassName)}>{label}</span>
    </span>
  );
}
