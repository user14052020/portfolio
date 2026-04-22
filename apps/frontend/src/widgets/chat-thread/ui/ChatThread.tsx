"use client";

import { GenerationPreviewSurface } from "@/entities/generation-job/ui/GenerationPreviewSurface";
import type { ThreadMessage } from "@/entities/chat-message/model/types";
import { AssistantPendingBubble } from "@/features/chat/ui/AssistantPendingBubble";
import type { Locale } from "@/shared/api/types";
import { cn } from "@/shared/lib/cn";
import { PillBadge } from "@/shared/ui/PillBadge";

function shouldDeferAssistantReply(message: ThreadMessage) {
  if (message.role !== "assistant") {
    return false;
  }

  return message.payload?.defer_reply_until_image_ready === true;
}

function isDeferredReplyReady(message: ThreadMessage) {
  return message.generation_job?.status === "completed" && Boolean(message.generation_job?.result_url);
}

function isGenerationInProgress(message: ThreadMessage) {
  return (
    message.generation_job?.status === "pending" ||
    message.generation_job?.status === "queued" ||
    message.generation_job?.status === "running"
  );
}

function shouldHideDeferredReplyText(message: ThreadMessage) {
  return message.payload?.hide_deferred_reply_text === true;
}

function shouldSuppressGenerationSurface(message: ThreadMessage) {
  return message.payload?.kind === "existing_generation_job_notice";
}

function getMessageBubbleClassName(role: ThreadMessage["role"]) {
  return cn(
    "inline-block w-fit max-w-[680px] whitespace-pre-wrap px-4 py-3.5 text-left text-sm leading-7 shadow-sm md:px-5",
    role === "assistant"
      ? "rounded-[28px] rounded-tl-lg border border-white/80 bg-white/88 text-[var(--text-secondary)] shadow-[var(--shadow-soft-sm)]"
      : "rounded-[28px] rounded-br-lg bg-[var(--surface-ink)] text-white shadow-[0_16px_38px_rgba(15,23,42,0.2)]",
  );
}

export function ChatThread({
  messages,
  locale,
  assistantLabel,
  welcomeText,
  errorMessage,
  isLoadingOlderHistory,
  isSending,
}: {
  messages: ThreadMessage[];
  locale: Locale;
  assistantLabel: string;
  welcomeText: string;
  errorMessage: string | null;
  isLoadingOlderHistory: boolean;
  isSending: boolean;
}) {
  const hasMessages = messages.length > 0;

  return (
    <div className="space-y-7">
      {isLoadingOlderHistory ? (
        <div className="text-center">
          <span className="rounded-[var(--radius-pill)] bg-white/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
            {locale === "ru" ? "Загружаю предыдущие сообщения" : "Loading older messages"}
          </span>
        </div>
      ) : null}

      {!hasMessages ? (
        <PillBadge tone="lilac" size="sm">
          {assistantLabel}
        </PillBadge>
      ) : null}

      {errorMessage ? (
        <div className="max-w-[680px] rounded-[28px] rounded-tl-lg border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm leading-7 text-rose-700 shadow-[var(--shadow-soft-sm)]">
          {errorMessage}
        </div>
      ) : null}

      {!hasMessages ? (
        <div className="max-w-[720px] space-y-3">
          <div className="w-fit max-w-[680px] rounded-[30px] rounded-tl-lg border border-white/80 bg-white/88 px-5 py-4 text-sm leading-7 text-[var(--text-secondary)] shadow-[var(--shadow-soft-sm)]">
            {welcomeText}
          </div>
        </div>
      ) : (
        messages.map((message) => {
          const deferReply = shouldDeferAssistantReply(message);
          const deferredReplyReady = isDeferredReplyReady(message);
          const hideDeferredReplyText = shouldHideDeferredReplyText(message);
          const showDeferredTyping =
            message.role === "assistant" && deferReply && !deferredReplyReady && isGenerationInProgress(message);
          const showAssistantText =
            message.role !== "assistant" ||
            !deferReply ||
            (deferredReplyReady && !hideDeferredReplyText) ||
            (!showDeferredTyping && !hideDeferredReplyText);
          const showAssistantGenerationFirst = message.role === "assistant" && deferReply;
          const suppressGenerationSurface = shouldSuppressGenerationSurface(message);

          return (
            <div key={message.id} className="space-y-3">
              <div
                className={
                  message.role === "assistant"
                    ? "max-w-[720px] space-y-2.5"
                    : "ml-auto max-w-[720px] space-y-2.5 text-right"
                }
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--text-muted)]">
                  {message.role === "assistant" ? assistantLabel : locale === "ru" ? "вы" : "you"}
                </p>

                {showAssistantGenerationFirst && message.generation_job && !suppressGenerationSurface ? (
                  <GenerationPreviewSurface job={message.generation_job} locale={locale} isPreparing={false} />
                ) : null}

                {showAssistantText ? (
                  <div className={getMessageBubbleClassName(message.role)}>
                    {message.content}
                  </div>
                ) : null}

                {showDeferredTyping ? <AssistantPendingBubble locale={locale} isGenerationIntent /> : null}

                {!showAssistantGenerationFirst &&
                message.role === "assistant" &&
                message.generation_job &&
                !suppressGenerationSurface ? (
                  <GenerationPreviewSurface job={message.generation_job} locale={locale} isPreparing={false} />
                ) : null}
              </div>
            </div>
          );
        })
      )}

      {isSending ? <AssistantPendingBubble locale={locale} isGenerationIntent={false} /> : null}
    </div>
  );
}
