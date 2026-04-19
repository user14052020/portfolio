"use client";

import { IconArrowUp } from "@tabler/icons-react";

import { ProgressRing } from "@/shared/ui/ProgressRing";

type ChatCooldownSendControlVariant = "dark" | "light";

export function ChatCooldownSendControl({
  isLocked,
  secondsRemaining,
  onSubmit,
  disabledReason,
  variant = "dark",
  disabled = false,
  cooldownSeconds = 60,
}: {
  isLocked: boolean;
  secondsRemaining: number;
  onSubmit: () => void;
  disabledReason?: string | null;
  variant?: ChatCooldownSendControlVariant;
  disabled?: boolean;
  cooldownSeconds?: number;
}) {
  const isDark = variant === "dark";
  const normalizedCooldownSeconds = Math.max(cooldownSeconds, 1);
  const clampedRemainingSeconds = Math.max(secondsRemaining, 0);
  const progressRatio = Math.min(clampedRemainingSeconds / normalizedCooldownSeconds, 1);
  const baseClassName = isDark
    ? "bg-slate-900 text-white hover:bg-slate-800 disabled:bg-slate-300"
    : "bg-white text-slate-900 hover:bg-slate-100 disabled:bg-slate-100";

  return (
    <button
      type="button"
      onClick={isLocked || disabled ? undefined : onSubmit}
      disabled={disabled}
      title={disabledReason ?? undefined}
      aria-label={disabledReason ?? (isLocked ? `Cooldown ${clampedRemainingSeconds}s` : "Send message")}
      className={`relative flex h-11 w-11 items-center justify-center self-end rounded-full transition ${baseClassName}`}
    >
      {isLocked ? (
        <>
          <ProgressRing
            size={40}
            strokeWidth={3}
            progress={progressRatio}
            trackColor={isDark ? "rgba(255,255,255,0.18)" : "rgba(15,23,42,0.16)"}
            progressColor={isDark ? "#ffffff" : "#0f172a"}
            className="absolute inset-0 h-full w-full -rotate-90"
          />
          <span className="relative text-[11px] font-semibold tabular-nums">{clampedRemainingSeconds}</span>
        </>
      ) : (
        <IconArrowUp size={18} />
      )}
    </button>
  );
}
