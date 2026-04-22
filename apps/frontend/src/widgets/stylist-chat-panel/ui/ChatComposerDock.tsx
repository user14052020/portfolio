"use client";

import type { RefObject } from "react";

import { ChatCooldownSendControl } from "@/features/chat-cooldown/ui/ChatCooldownSendControl";
import { InputSurface } from "@/shared/ui/InputSurface";

export function ChatComposerDock({
  textareaRef,
  input,
  placeholder,
  title,
  disabled,
  textareaDisabled,
  isSendLocked,
  isCooldownActive,
  cooldownRemainingSeconds,
  cooldownSeconds,
  sendControlDisabledReason,
  onInputChange,
  onSubmit,
}: {
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  input: string;
  placeholder: string;
  title?: string;
  disabled: boolean;
  textareaDisabled: boolean;
  isSendLocked: boolean;
  isCooldownActive: boolean;
  cooldownRemainingSeconds: number;
  cooldownSeconds: number;
  sendControlDisabledReason?: string | null;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
}) {
  return (
    <InputSurface disabled={disabled} density="spacious" tone="elevated" className="rounded-[32px]">
      <div className="flex items-end gap-3">
        <textarea
          ref={textareaRef}
          value={input}
          disabled={textareaDisabled}
          title={title}
          onChange={(event) => onInputChange(event.currentTarget.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              if (!isSendLocked) {
                onSubmit();
              }
            }
          }}
          rows={1}
          placeholder={placeholder}
          className="min-h-[48px] flex-1 resize-none overflow-hidden border-0 bg-transparent py-[11px] text-base leading-6 text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] disabled:cursor-not-allowed disabled:text-slate-400"
        />
        <ChatCooldownSendControl
          isLocked={isCooldownActive}
          secondsRemaining={cooldownRemainingSeconds}
          cooldownSeconds={cooldownSeconds}
          onSubmit={onSubmit}
          disabled={isSendLocked}
          disabledReason={sendControlDisabledReason}
          variant="dark"
        />
      </div>
    </InputSurface>
  );
}
