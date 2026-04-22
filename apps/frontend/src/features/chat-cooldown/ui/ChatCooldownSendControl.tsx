"use client";

import { IconArrowUp } from "@tabler/icons-react";

import { buildChatCooldownSendControlState } from "@/features/chat-cooldown/model/cooldownSendControl";
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
  const controlState = buildChatCooldownSendControlState({
    isLocked,
    secondsRemaining,
    disabledReason,
    disabled,
    cooldownSeconds,
  });
  const baseClassName = isDark
    ? "bg-[var(--surface-ink)] text-white shadow-[0_16px_34px_rgba(15,23,42,0.28)] hover:bg-black disabled:bg-slate-300 disabled:shadow-none"
    : "bg-white text-slate-900 shadow-[var(--shadow-soft-sm)] hover:bg-slate-100 disabled:bg-slate-100 disabled:shadow-none";

  return (
    <button
      type="button"
      onClick={controlState.canSubmit ? onSubmit : undefined}
      disabled={disabled}
      aria-disabled={!controlState.canSubmit}
      title={controlState.title}
      aria-label={controlState.ariaLabel}
      className={[
        "relative flex h-12 w-12 items-center justify-center self-end rounded-full transition duration-200 active:scale-95",
        baseClassName,
      ].join(" ")}
    >
      {isLocked ? (
        <ProgressRing
          size={48}
          strokeWidth={3.4}
          progress={controlState.progressRatio}
          tone={isDark ? "dark" : "light"}
          label={controlState.clampedRemainingSeconds}
          labelClassName="text-[11px] font-semibold tabular-nums"
          className="absolute inset-0 h-full w-full"
        />
      ) : (
        <IconArrowUp size={18} />
      )}
    </button>
  );
}
