import { ChatModeChip } from "@/shared/ui/ChatModeChip";
import { PillBadge } from "@/shared/ui/PillBadge";

type ChatAssistantStatusTone = "online" | "generating" | "offline";

export function ChatAssistantHeader({
  assistantName,
  subtitle,
  statusLabel,
  statusTone,
  modeLabel,
}: {
  assistantName: string;
  subtitle: string;
  statusLabel: string;
  statusTone: ChatAssistantStatusTone;
  modeLabel: string;
}) {
  return (
    <div className="flex flex-col gap-4 border-b border-[var(--border-soft)] bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(247,245,240,0.78))] px-5 py-5 md:flex-row md:items-center md:justify-between md:px-6">
      <div className="min-w-0 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-display text-base text-[var(--text-primary)]">{assistantName}</p>
          <PillBadge tone="subtle" size="sm">
            stylist
          </PillBadge>
        </div>
        <p className="max-w-2xl text-sm leading-6 text-[var(--text-secondary)]">{subtitle}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <ChatModeChip label={modeLabel} tone="neutral" />
        <ChatModeChip label={statusLabel} tone={statusTone} />
      </div>
    </div>
  );
}
