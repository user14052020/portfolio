"use client";

import { GenerationPreviewSurface } from "@/entities/generation-job/ui/GenerationPreviewSurface";
import type { ThreadMessage } from "@/entities/chat-message/model/types";
import { AssistantPendingBubble } from "@/features/chat/ui/AssistantPendingBubble";
import type { Locale } from "@/shared/api/types";
import { cn } from "@/shared/lib/cn";

function shouldDeferAssistantReply(message: ThreadMessage) {
  if (message.role !== "assistant") {
    return false;
  }

  return message.payload?.defer_reply_until_image_ready === true;
}

function isDeferredReplyReady(message: ThreadMessage) {
  return message.generation_job?.status === "completed" && Boolean(message.generation_job?.result_url);
}

function shouldSuppressGenerationSurface(message: ThreadMessage) {
  return message.payload?.kind === "existing_generation_job_notice";
}

function getMessageBubbleClassName(role: ThreadMessage["role"]) {
  return cn(
    "inline-block w-fit max-w-[620px] px-4 py-3 text-left text-sm leading-7 shadow-sm",
    role === "assistant"
      ? "rounded-[24px] rounded-tl-md border border-slate-200 bg-white/95 text-slate-700"
      : "rounded-[24px] rounded-br-md bg-slate-900 text-white shadow-[0_14px_30px_rgba(15,23,42,0.16)]",
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
    <div className="space-y-6">
      {isLoadingOlderHistory ? (
        <div className="text-center">
          <span className="text-[11px] uppercase tracking-[0.18em] text-slate-400">
            {locale === "ru" ? "Загружаю предыдущие сообщения" : "Loading older messages"}
          </span>
        </div>
      ) : null}

      {!hasMessages ? (
        <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">{assistantLabel}</p>
      ) : null}

      {errorMessage ? (
        <div className="max-w-[620px] rounded-[24px] rounded-tl-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-7 text-rose-700 shadow-sm">
          {errorMessage}
        </div>
      ) : null}

      {!hasMessages ? (
        <div className="max-w-[620px] space-y-2">
          <div className="w-fit max-w-[620px] rounded-[24px] rounded-tl-md border border-slate-200 bg-white/95 px-4 py-3 text-sm leading-7 text-slate-700 shadow-sm">
            {welcomeText}
          </div>
        </div>
      ) : (
        messages.map((message) => {
          const deferReply = shouldDeferAssistantReply(message);
          const deferredReplyReady = isDeferredReplyReady(message);
          const showAssistantText = message.role !== "assistant" || !deferReply || deferredReplyReady;
          const showAssistantGenerationFirst = message.role === "assistant" && deferReply;
          const suppressGenerationSurface = shouldSuppressGenerationSurface(message);

          return (
            <div key={message.id} className="space-y-3">
              <div
                className={
                  message.role === "assistant"
                    ? "max-w-[620px] space-y-2"
                    : "ml-auto max-w-[620px] space-y-2 text-right"
                }
              >
                <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">
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
