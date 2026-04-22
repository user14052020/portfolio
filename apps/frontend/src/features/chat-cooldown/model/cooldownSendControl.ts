export type ChatCooldownSendControlState = {
  normalizedCooldownSeconds: number;
  clampedRemainingSeconds: number;
  progressRatio: number;
  canSubmit: boolean;
  ariaLabel: string;
  title?: string;
};

function toFiniteNumber(value: number, fallback: number) {
  return Number.isFinite(value) ? value : fallback;
}

export function buildChatCooldownSendControlState({
  isLocked,
  secondsRemaining,
  disabledReason,
  disabled = false,
  cooldownSeconds = 60,
}: {
  isLocked: boolean;
  secondsRemaining: number;
  disabledReason?: string | null;
  disabled?: boolean;
  cooldownSeconds?: number;
}): ChatCooldownSendControlState {
  const normalizedCooldownSeconds = Math.max(toFiniteNumber(cooldownSeconds, 60), 1);
  const clampedRemainingSeconds = Math.max(toFiniteNumber(secondsRemaining, 0), 0);
  const progressRatio = Math.min(clampedRemainingSeconds / normalizedCooldownSeconds, 1);
  const canSubmit = !isLocked && !disabled;
  return {
    normalizedCooldownSeconds,
    clampedRemainingSeconds,
    progressRatio,
    canSubmit,
    ariaLabel: disabledReason ?? (isLocked ? `Cooldown ${clampedRemainingSeconds}s` : "Send message"),
    title: disabledReason ?? undefined,
  };
}
