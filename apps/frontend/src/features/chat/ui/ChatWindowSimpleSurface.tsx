"use client";

import { ActionIcon, Loader } from "@mantine/core";
import { IconArrowUp, IconClockHour4, IconRefresh } from "@tabler/icons-react";
import { useLayoutEffect, useRef } from "react";

import { GenerationPreviewSurface } from "@/entities/generation-job/ui/GenerationPreviewSurface";
import { useStylistChat } from "@/features/chat/model/useStylistChatSimple";
import { AssistantPendingBubble } from "@/features/chat/ui/AssistantPendingBubble";
import { GenerationStatusRail } from "@/features/chat/ui/GenerationStatusRail";
import type { SiteSettings } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";

const RU_ASSISTANT_FALLBACK = "Валентин";
const RU_ONLINE = "онлайн";
const RU_GENERATING = "генерация";
const RU_OFFLINE = "офлайн";
const RU_YOU = "вы";
const RU_CHAT_SUBTITLE =
  "Говорю как историк моды и портной: помогаю собрать образ и при необходимости визуализировать его в flat lay.";
const RU_CHAT_WELCOME =
  "Можете просто спросить, что надеть и в каком случае, или начать с готового сценария ниже. Если нужно собрать образ вокруг конкретной вещи, начните с фото.";
const RU_CHAT_PLACEHOLDER =
  "Напишите, что хотите надеть, куда идёте, или загрузите фото вещи...";
const TOP_HISTORY_LOAD_THRESHOLD_PX = 48;

type QuickAction = {
  kind: "pair" | "style" | "occasion";
  label: string;
  message: string;
  autoGenerate?: boolean;
};

function getQuickActions(locale: "ru" | "en"): QuickAction[] {
  if (locale === "ru") {
    return [
      {
        kind: "pair",
        label: "Подобрать к этой вещи",
        message: "Помоги подобрать к этой вещи что-то подходящее.",
        autoGenerate: true,
      },
      {
        kind: "style",
        label: "Попробовать другой стиль",
        message: "Хочу попробовать другой стиль.",
        autoGenerate: true,
      },
      {
        kind: "occasion",
        label: "Что надеть на событие",
        message: "Подскажи, что надеть на важное событие.",
      },
    ];
  }

  return [
    {
      kind: "pair",
      label: "Style this item",
      message: "Help me pair something with this item.",
      autoGenerate: true,
    },
    {
      kind: "style",
      label: "Try another style",
      message: "I want to try a different style.",
      autoGenerate: true,
    },
    {
      kind: "occasion",
      label: "What should I wear?",
      message: "Help me decide what to wear for an important occasion.",
    },
  ];
}

function getStatefulQuickActions(locale: "ru" | "en") {
  if (locale === "ru") {
    return [
      {
        kind: "pair" as const,
        label: "Подобрать к вещи",
        message: "Хочу подобрать образ к конкретной вещи.",
        autoGenerate: false,
        requestedIntent: "garment_matching" as const,
      },
      {
        kind: "style" as const,
        label: "Попробовать другой стиль",
        message: "Хочу попробовать другой стиль.",
        autoGenerate: true,
        requestedIntent: "style_exploration" as const,
      },
      {
        kind: "occasion" as const,
        label: "Что надеть на событие",
        message: "Подскажи, что надеть на важное событие.",
        requestedIntent: "occasion_outfit" as const,
      },
    ];
  }

  return [
    {
      kind: "pair" as const,
      label: "Style a garment",
      message: "I want to build an outfit around a specific garment.",
      autoGenerate: false,
      requestedIntent: "garment_matching" as const,
    },
    {
      kind: "style" as const,
      label: "Try another style",
      message: "I want to try a different style.",
      autoGenerate: true,
      requestedIntent: "style_exploration" as const,
    },
    {
      kind: "occasion" as const,
      label: "What should I wear?",
      message: "Help me decide what to wear for an important occasion.",
      requestedIntent: "occasion_outfit" as const,
    },
  ];
}

void getQuickActions;
void RU_CHAT_WELCOME;
void RU_CHAT_PLACEHOLDER;

function QuickActionIcon({ kind }: { kind: QuickAction["kind"] | "upload" }) {
  if (kind === "pair") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M8 6c0-1.1.9-2 2-2h4c1.1 0 2 .9 2 2" />
        <path d="M12 8v2" />
        <path d="M6 9.5 12 14l6-4.5" />
        <path d="M6 9.5V18a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V9.5" />
      </svg>
    );
  }

  if (kind === "style") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 3l1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7L12 3Z" />
        <path d="M18.5 15.5 19.4 18l2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9.9-2.5Z" />
      </svg>
    );
  }

  if (kind === "occasion") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="4" y="5" width="16" height="15" rx="2" />
        <path d="M8 3v4M16 3v4M4 10h16" />
        <path d="M8 14h3M13 14h3M8 17h3" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M16.5 6.5 9 14a3 3 0 1 0 4.2 4.2l7.1-7.1a5 5 0 0 0-7.1-7.1L5.8 11.4" />
    </svg>
  );
}

function getQuickActionButtonClass(isActive = false) {
  return isActive
    ? "inline-flex items-center gap-2 border border-slate-900 bg-slate-900 px-3 py-2 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
    : "inline-flex items-center gap-2 border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-white disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400";
}

function formatSecondsLabel(locale: "ru" | "en", seconds: number) {
  if (seconds <= 0) {
    return locale === "ru" ? "сейчас" : "now";
  }

  return locale === "ru" ? `через ${seconds}с` : `in ${seconds}s`;
}

function isGenerationActive(status: string | undefined) {
  return status === "pending" || status === "queued" || status === "running";
}

function isNearBottom(container: HTMLDivElement) {
  return container.scrollHeight - container.scrollTop - container.clientHeight <= 72;
}

function shouldDeferAssistantReply(message: {
  role: "user" | "assistant" | "system";
  generation_job?: { status: string; result_url?: string | null } | null;
  payload: Record<string, unknown>;
}) {
  if (message.role !== "assistant") {
    return false;
  }

  return message.payload?.defer_reply_until_image_ready === true;
}

function isDeferredReplyReady(message: {
  generation_job?: { status: string; result_url?: string | null } | null;
}) {
  return message.generation_job?.status === "completed" && Boolean(message.generation_job?.result_url);
}

function shouldSuppressGenerationSurface(message: {
  payload: Record<string, unknown>;
}) {
  return message.payload?.kind === "existing_generation_job_notice";
}

function getStatusBadge(locale: "ru" | "en", availability: "online" | "offline", isGenerating: boolean) {
  if (availability === "offline") {
    return locale === "ru"
      ? { label: RU_OFFLINE, className: "border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-medium text-rose-700" }
      : { label: "offline", className: "border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-medium text-rose-700" };
  }

  if (isGenerating) {
    return {
      label: locale === "ru" ? RU_GENERATING : "generating",
      className: "border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700",
    };
  }

  return locale === "ru"
    ? { label: RU_ONLINE, className: "border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700" }
    : { label: "online", className: "border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700" };
}

export function ChatWindowSimpleSurface({ settings }: { settings: SiteSettings }) {
  const { locale } = useI18n();
  const chat = useStylistChat(locale);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const prependScrollStateRef = useRef<{ scrollHeight: number; scrollTop: number } | null>(null);
  const hasInitialScrollRef = useRef(false);
  const shouldStickToBottomRef = useRef(true);
  const previousMessageCountRef = useRef(chat.messages.length);

  const quickActions = getStatefulQuickActions(locale);
  const assistantName =
    (locale === "ru" ? settings.assistant_name_ru : settings.assistant_name_en) ||
    (locale === "ru" ? RU_ASSISTANT_FALLBACK : "Jose");
  const assistantLabel = assistantName;
  const hasMessages = chat.messages.length > 0;
  const chatSubtitle =
    locale === "ru"
      ? RU_CHAT_SUBTITLE
      : "I speak like a fashion historian and tailor: I help shape outfits and, when needed, visualize them as flat lays.";
  const chatWelcome =
    locale === "ru"
      ? "Можете просто спросить, что надеть и по какому поводу, или начать с готового сценария ниже. Если хотите собрать образ вокруг конкретной вещи, начните с её короткого текстового описания."
      : "You can simply ask what to wear and for which occasion, or start with one of the ready-made scenarios below. If you want to build a look around a specific garment, start with a short text description.";
  const chatPlaceholder =
    locale === "ru"
      ? "Опишите вещь, событие или желаемый стиль..."
      : "Describe the garment, occasion, or style direction...";
  const statusBadge = getStatusBadge(locale, chat.chatAvailability, isGenerationActive(chat.activeJob?.status));
  const isInputLocked = chat.isSendLocked;
  const isEditorLocked = chat.isEditorLocked;
  const showQueueCard = chat.isGenerationQueued && Boolean(chat.activeJob);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "0px";
    const nextHeight = Math.min(Math.max(textarea.scrollHeight, 44), 240);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 240 ? "auto" : "hidden";
  }, [chat.input]);

  useLayoutEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return;
    }

    if (prependScrollStateRef.current) {
      const { scrollHeight, scrollTop } = prependScrollStateRef.current;
      container.scrollTop = scrollTop + (container.scrollHeight - scrollHeight);
      prependScrollStateRef.current = null;
      previousMessageCountRef.current = chat.messages.length;
      return;
    }

    const messageCountIncreased = chat.messages.length > previousMessageCountRef.current;
    const shouldScrollToBottom =
      !hasInitialScrollRef.current ||
      chat.isSending ||
      chat.isGenerationPreparing ||
      (messageCountIncreased && shouldStickToBottomRef.current);

    if (shouldScrollToBottom) {
      container.scrollTop = container.scrollHeight;
      shouldStickToBottomRef.current = true;
      hasInitialScrollRef.current = true;
    }

    previousMessageCountRef.current = chat.messages.length;
  }, [chat.messages.length, chat.isSending, chat.isGenerationPreparing, chat.activeJob?.result_url]);

  return (
    <section className="space-y-6">
      <div className="border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <p className="font-display text-sm text-slate-900">{assistantName}</p>
            <p className="text-sm text-slate-500">{chatSubtitle}</p>
          </div>
          <div className={statusBadge.className}>{statusBadge.label}</div>
        </div>

        <div
          ref={scrollContainerRef}
          className="h-[480px] overflow-y-auto px-5 py-6"
          onScroll={(event) => {
            const container = event.currentTarget;
            shouldStickToBottomRef.current = isNearBottom(container);

            if (
              container.scrollTop <= TOP_HISTORY_LOAD_THRESHOLD_PX &&
              chat.hasMoreHistory &&
              !chat.isLoadingOlderHistory
            ) {
              prependScrollStateRef.current = {
                scrollHeight: container.scrollHeight,
                scrollTop: container.scrollTop,
              };
              void chat.loadOlderHistory();
            }
          }}
        >
          <div className="space-y-6">
            {chat.isLoadingOlderHistory ? (
              <div className="text-center">
                <span className="text-[11px] uppercase tracking-[0.18em] text-slate-400">
                  {locale === "ru" ? "Загружаю предыдущие сообщения" : "Loading older messages"}
                </span>
              </div>
            ) : null}

            {!hasMessages ? (
              <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">{assistantLabel}</p>
            ) : null}

            {chat.errorMessage ? (
              <div className="max-w-[620px] border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-7 text-rose-700">
                {chat.errorMessage}
              </div>
            ) : null}

            {!hasMessages ? (
              <div className="max-w-[620px] space-y-2">
                <div className="w-fit max-w-[620px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-7 text-slate-700">
                  {chatWelcome}
                </div>
              </div>
            ) : (
              chat.messages.map((message) => {
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
                        {message.role === "assistant" ? assistantLabel : locale === "ru" ? RU_YOU : "you"}
                      </p>

                      {showAssistantGenerationFirst && message.generation_job && !suppressGenerationSurface ? (
                        <GenerationPreviewSurface job={message.generation_job} locale={locale} isPreparing={false} />
                      ) : null}

                      {showAssistantText ? (
                        <div
                          className={
                            message.role === "assistant"
                              ? "inline-block w-fit max-w-[620px] border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm leading-7 text-slate-700"
                              : "inline-block w-fit max-w-[620px] bg-slate-900 px-4 py-3 text-left text-sm leading-7 text-white"
                          }
                        >
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

            {chat.isSending && !chat.isGenerationPreparing ? (
              <AssistantPendingBubble locale={locale} isGenerationIntent={false} />
            ) : null}
          </div>
        </div>

        <div className="border-t border-slate-200 px-4 py-4">
          <GenerationStatusRail
            job={chat.activeJob}
            locale={locale}
            isPreparing={chat.isGenerationPreparing}
          />

          {showQueueCard && chat.activeJob ? (
            <div className="mb-3 flex items-start justify-between gap-3 border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <div className="space-y-1">
                <p className="font-medium">
                  {locale === "ru"
                    ? `Очередь на генерацию: позиция ${chat.activeJob.queue_position ?? 1}`
                    : `Generation queue: position ${chat.activeJob.queue_position ?? 1}`}
                </p>
                <p className="text-xs leading-5 text-amber-800">
                  {locale === "ru"
                    ? "Пока задача ждёт своей очереди, можно продолжать общаться в чате. Позиция обновляется вручную."
                    : "While the image waits in the queue, you can continue chatting. Queue position is refreshed manually."}
                </p>
              </div>
              <button
                type="button"
                onClick={() => void chat.handleRefreshQueuePosition()}
                disabled={chat.queueRefreshRemainingSeconds > 0 || chat.isRefreshingQueue}
                className="inline-flex items-center gap-2 border border-amber-300 bg-white px-3 py-2 text-xs font-medium uppercase tracking-[0.18em] text-amber-900 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:border-amber-200 disabled:bg-amber-100 disabled:text-amber-500"
              >
                {chat.isRefreshingQueue ? <Loader size={14} color="currentColor" /> : <IconRefresh size={14} />}
                <span>
                  {chat.queueRefreshRemainingSeconds > 0
                    ? formatSecondsLabel(locale, chat.queueRefreshRemainingSeconds)
                    : locale === "ru"
                      ? "обновить"
                      : "refresh"}
                </span>
              </button>
            </div>
          ) : (
            <div className="mb-3 flex flex-wrap gap-2">
              {quickActions.map((action) => (
                <button
                  key={action.label}
                  type="button"
                  disabled={chat.isGenerationActionLocked}
                  onClick={() =>
                    void chat.handleQuickAction(
                      action.message,
                      action.autoGenerate,
                      action.requestedIntent
                    )
                  }
                  className={getQuickActionButtonClass()}
                >
                  <QuickActionIcon kind={action.kind} />
                  <span>{action.label}</span>
                </button>
              ))}
            </div>
          )}

          <div className="border border-slate-200 bg-white px-3 py-2">
            <div className="flex items-end gap-3">
              <textarea
                ref={textareaRef}
                value={chat.input}
                disabled={isEditorLocked}
                onChange={(event) => chat.setInput(event.currentTarget.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    if (!chat.isSendLocked) {
                      void chat.handleSend();
                    }
                  }
                }}
                rows={1}
                placeholder={chatPlaceholder}
                className="min-h-[44px] flex-1 resize-none overflow-hidden border-0 bg-transparent py-[10px] text-base leading-6 text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:text-slate-400"
              />
              <ActionIcon
                radius={0}
                size="xl"
                color="dark"
                onClick={() => void chat.handleSend()}
                disabled={isInputLocked}
                className="h-11 w-11 self-end rounded-none bg-slate-900 text-white transition hover:bg-slate-800 disabled:bg-slate-300"
              >
                {chat.isSending ? (
                  <IconClockHour4 size={18} className="text-slate-300" />
                ) : chat.messageCooldownRemainingSeconds > 0 ? (
                  <div className="flex flex-col items-center justify-center leading-none text-white">
                    <IconClockHour4 size={14} />
                    <span className="mt-0.5 text-[9px] font-medium tabular-nums">
                      {Math.min(chat.messageCooldownRemainingSeconds, 99)}
                    </span>
                  </div>
                ) : (
                  <IconArrowUp size={18} />
                )}
              </ActionIcon>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
