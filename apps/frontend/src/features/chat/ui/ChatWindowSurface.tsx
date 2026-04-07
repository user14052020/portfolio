"use client";

import { ActionIcon, Loader } from "@mantine/core";
import { IconArrowUp, IconRefresh } from "@tabler/icons-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";

import { GenerationResultSurface } from "@/entities/generation-job/ui/GenerationResultSurface";
import { useStylistChat } from "@/features/chat/model/useStylistChat";
import { AssistantPendingBubble } from "@/features/chat/ui/AssistantPendingBubble";
import type { SiteSettings } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";

const RU_ASSISTANT_FALLBACK = "\u0412\u0430\u043b\u0435\u043d\u0442\u0438\u043d";
const RU_ONLINE = "\u043e\u043d\u043b\u0430\u0439\u043d";
const RU_YOU = "\u0432\u044b";
const RU_CHAT_SUBTITLE = "\u042f \u043f\u043e\u043c\u043e\u0433\u0430\u044e \u0441\u043e\u0431\u0440\u0430\u0442\u044c \u0441\u0442\u0438\u043b\u044c\u043d\u044b\u0439 \u0438 \u0432\u0437\u0440\u043e\u0441\u043b\u044b\u0439 \u0433\u0430\u0440\u0434\u0435\u0440\u043e\u0431.";
const RU_CHAT_WELCOME =
  "\u041e\u043f\u0438\u0448\u0438\u0442\u0435 \u0432\u0435\u0449\u044c, \u0441\u0442\u0438\u043b\u044c \u0438\u043b\u0438 \u043f\u043e\u0432\u043e\u0434, \u0438 \u044f \u0441\u043e\u0431\u0435\u0440\u0443 \u043e\u0431\u0440\u0430\u0437 \u0432 \u0441\u0442\u043e\u0440\u043e\u043d\u0443 \u043a\u043b\u0430\u0441\u0441\u0438\u043a\u0438, \u0434\u0435\u043b\u043e\u0432\u043e\u0433\u043e \u0438\u043b\u0438 \u0447\u0438\u0441\u0442\u043e\u0433\u043e smart-casual. \u0415\u0441\u043b\u0438 \u0437\u043d\u0430\u0435\u0442\u0435 \u043f\u043e\u043b, \u0440\u043e\u0441\u0442 \u0438 \u0432\u0435\u0441, \u043c\u043e\u0436\u043d\u043e \u0441\u0440\u0430\u0437\u0443 \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0438\u0445 \u0432 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0438.";
const RU_CHAT_PLACEHOLDER =
  "\u041e\u043f\u0438\u0448\u0438\u0442\u0435 \u0432\u0435\u0449\u044c, \u0441\u0442\u0438\u043b\u044c, \u043f\u043e\u0432\u043e\u0434 \u0438, \u0435\u0441\u043b\u0438 \u043d\u0443\u0436\u043d\u043e, \u0441\u0440\u0430\u0437\u0443 \u0443\u043a\u0430\u0436\u0438\u0442\u0435 \u043f\u043e\u043b, \u0440\u043e\u0441\u0442 \u0438 \u0432\u0435\u0441...";
const RU_BACKEND_CONNECTED = "backend \u043d\u0430 \u0441\u0432\u044f\u0437\u0438";
const RU_BACKEND_CONNECTING = "\u043f\u0440\u043e\u0432\u0435\u0440\u044f\u044e backend";
const RU_BACKEND_UNAVAILABLE = "backend \u043d\u0435 \u043e\u0442\u0432\u0435\u0447\u0430\u0435\u0442";
const RU_GENERATING = "\u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f";
const RU_OFFLINE = "\u043e\u0444\u043b\u0430\u0439\u043d";
const RU_GENDER = "\u041f\u043e\u043b";
const RU_HEIGHT = "\u0420\u043e\u0441\u0442";
const RU_WEIGHT = "\u0412\u0435\u0441";
const RU_GENERATE_IMAGE = "\u0413\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435";
const RU_MALE = "\u041c\u0443\u0436\u0447\u0438\u043d\u0430";
const RU_FEMALE = "\u0416\u0435\u043d\u0449\u0438\u043d\u0430";
const RU_PROFILE_HINT =
  "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u043f\u043e\u043b, \u0440\u043e\u0441\u0442 \u0438 \u0432\u0435\u0441, \u0447\u0442\u043e\u0431\u044b \u0441\u0442\u0438\u043b\u0438\u0441\u0442 \u0442\u043e\u0447\u043d\u0435\u0435 \u0443\u0447\u0435\u043b \u043f\u0440\u043e\u043f\u043e\u0440\u0446\u0438\u0438.";
const DEFAULT_VISIBLE_MESSAGES = 14;
const VISIBLE_MESSAGES_STEP = 10;
const TOP_REVEAL_THRESHOLD_PX = 48;

function getBackendStatusLabel(locale: "ru" | "en", status: "connecting" | "connected" | "error") {
  if (locale === "ru") {
    return status === "connected"
      ? RU_BACKEND_CONNECTED
      : status === "connecting"
        ? RU_BACKEND_CONNECTING
        : RU_BACKEND_UNAVAILABLE;
  }

  return status === "connected"
    ? "backend connected"
    : status === "connecting"
      ? "checking backend"
      : "backend unavailable";
}

function isGenerationActive(status: string | undefined) {
  return status === "pending" || status === "queued" || status === "running";
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

function getChatPresenceBadge(
  locale: "ru" | "en",
  availability: "online" | "offline",
  isGenerating: boolean
) {
  if (availability === "offline") {
    return locale === "ru"
      ? { label: RU_OFFLINE, className: "border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-medium text-rose-700" }
      : { label: "offline", className: "border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-medium text-rose-700" };
  }

  if (isGenerating) {
    return locale === "ru"
      ? { label: RU_GENERATING, className: "border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700" }
      : { label: "generating", className: "border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700" };
  }

  return locale === "ru"
    ? { label: RU_ONLINE, className: "border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700" }
    : { label: "online", className: "border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700" };
}

function formatSecondsLabel(locale: "ru" | "en", seconds: number) {
  if (seconds <= 0) {
    return locale === "ru" ? "сейчас" : "now";
  }

  return locale === "ru" ? `через ${seconds}с` : `in ${seconds}s`;
}

export function ChatWindowSurface({ settings }: { settings: SiteSettings }) {
  const { locale } = useI18n();
  const chat = useStylistChat(locale);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [visibleMessageCount, setVisibleMessageCount] = useState(DEFAULT_VISIBLE_MESSAGES);
  const assistantName =
    (locale === "ru" ? settings.assistant_name_ru : settings.assistant_name_en) ||
    (locale === "ru" ? RU_ASSISTANT_FALLBACK : "Jose");
  const assistantLabel = assistantName;
  const hasMessages = chat.messages.length > 0;
  const chatSubtitle = locale === "ru" ? RU_CHAT_SUBTITLE : "I help shape a sharper, more grown-up wardrobe.";
  const chatWelcome =
    locale === "ru"
      ? RU_CHAT_WELCOME
      : "Describe the garment, style, or occasion and I will shape the look toward classic, business, or clean smart-casual styling. If you know your gender, height, and weight, you can include them in the same message.";
  const chatPlaceholder =
    locale === "ru"
      ? RU_CHAT_PLACEHOLDER
      : "Describe the garment, style direction, occasion, and optionally your gender, height, and weight...";
  const backendStatusLabel = getBackendStatusLabel(locale, chat.backendState);
  const generationActive = isGenerationActive(chat.activeJob?.status);
  const chatPresenceBadge = getChatPresenceBadge(locale, chat.chatAvailability, generationActive);
  const isInputLocked = chat.isSendLocked;
  const isEditorLocked = chat.isEditorLocked;
  const showQueueCard = chat.isGenerationQueued && Boolean(chat.activeJob);
  const visibleMessages = hasMessages ? chat.messages.slice(-visibleMessageCount) : [];
  const hiddenMessageCount = Math.max(chat.messages.length - visibleMessages.length, 0);

  useEffect(() => {
    setVisibleMessageCount((current) => {
      if (chat.messages.length === 0) {
        return DEFAULT_VISIBLE_MESSAGES;
      }

      const normalizedCount = Math.max(current, DEFAULT_VISIBLE_MESSAGES);
      return Math.min(normalizedCount, chat.messages.length);
    });
  }, [chat.messages.length]);

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
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [chat.messages.length, chat.isGenerationPreparing, chat.activeJob?.updated_at]);

  return (
    <section className="space-y-6">
      <div className="border border-slate-200 bg-white">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <p className="font-display text-sm text-slate-900">{assistantName}</p>
            <p className="text-sm text-slate-500">{chatSubtitle}</p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={
                chat.backendState === "connected"
                  ? "border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700"
                  : chat.backendState === "connecting"
                    ? "border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700"
                    : "border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-medium text-rose-700"
              }
            >
              {backendStatusLabel}
            </div>
            <div
              className={chatPresenceBadge.className}
            >
              {chatPresenceBadge.label}
            </div>
          </div>
        </div>
        <div
          ref={scrollContainerRef}
          className="h-[480px] overflow-y-auto px-5 py-6"
          onScroll={(event) => {
            if (event.currentTarget.scrollTop > TOP_REVEAL_THRESHOLD_PX || hiddenMessageCount === 0) {
              return;
            }

            setVisibleMessageCount((current) => Math.min(chat.messages.length, current + VISIBLE_MESSAGES_STEP));
          }}
        >
          <div className="space-y-6">
            <div className="space-y-6">
              {hiddenMessageCount > 0 ? (
                <div className="text-center">
                  <button
                    type="button"
                    onClick={() => setVisibleMessageCount((current) => Math.min(chat.messages.length, current + VISIBLE_MESSAGES_STEP))}
                    className="border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium uppercase tracking-[0.18em] text-slate-500 transition hover:border-slate-300 hover:bg-white"
                  >
                    {locale === "ru"
                      ? `Показать еще ${Math.min(VISIBLE_MESSAGES_STEP, hiddenMessageCount)}`
                      : `Show ${Math.min(VISIBLE_MESSAGES_STEP, hiddenMessageCount)} more`}
                  </button>
                </div>
              ) : null}

              {!hasMessages ? (
                <p className="text-xs font-medium uppercase tracking-[0.24em] text-slate-400">
                  {assistantLabel}
                </p>
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
                visibleMessages.map((message) => {
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
                          {message.role === "assistant"
                            ? assistantLabel
                            : locale === "ru"
                              ? RU_YOU
                              : "you"}
                        </p>

                        {showAssistantGenerationFirst && message.generation_job && !suppressGenerationSurface ? (
                          <GenerationResultSurface
                            job={message.generation_job}
                            locale={locale}
                            assistantLabel={assistantLabel}
                            isPreparing={false}
                          />
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
                      </div>

                      {!showAssistantGenerationFirst &&
                      message.role === "assistant" &&
                      message.generation_job &&
                      !suppressGenerationSurface ? (
                        <GenerationResultSurface
                          job={message.generation_job}
                          locale={locale}
                          assistantLabel={assistantLabel}
                          isPreparing={false}
                        />
                      ) : null}
                    </div>
                  );
                })
              )}
              {chat.isSending && chat.isGenerationPreparing ? (
                <GenerationResultSurface
                  job={chat.activeJob}
                  locale={locale}
                  assistantLabel={assistantLabel}
                  isPreparing
                />
              ) : null}
              {chat.isSending && !chat.isGenerationPreparing ? (
                <AssistantPendingBubble
                  locale={locale}
                  isGenerationIntent={false}
                />
              ) : null}
              <div ref={bottomRef} />
            </div>
          </div>
        </div>
        <div className="border-t border-slate-200 px-4 py-4">
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
                    ? "Пока изображение ждёт своей очереди, можно продолжать переписку. Позиция обновляется вручную."
                    : "While the image is waiting in the queue, you can keep chatting. Queue position is refreshed manually."}
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
          ) : null}
          <div className="border border-slate-200 bg-white px-3 py-2">
            <div className="mb-3 grid gap-3 md:grid-cols-[1.2fr_1fr_1fr_auto]">
              <label className="space-y-1">
                <span className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-500">
                  {locale === "ru" ? RU_GENDER : "Gender"}
                </span>
                <select
                  value={chat.profileGender}
                  onChange={(event) => chat.setProfileGender(event.currentTarget.value)}
                  disabled={isEditorLocked}
                  className="h-11 w-full border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                >
                  <option value="">{locale === "ru" ? "Не указан" : "Not set"}</option>
                  <option value="male">{locale === "ru" ? RU_MALE : "Male"}</option>
                  <option value="female">{locale === "ru" ? RU_FEMALE : "Female"}</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-500">
                  {locale === "ru" ? RU_HEIGHT : "Height"}
                </span>
                <input
                  inputMode="numeric"
                  value={chat.bodyHeightCm}
                  onChange={(event) => chat.setBodyHeightCm(event.currentTarget.value)}
                  disabled={isEditorLocked}
                  placeholder={locale === "ru" ? "182 см" : "182 cm"}
                  className="h-11 w-full border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                />
              </label>
              <label className="space-y-1">
                <span className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-500">
                  {locale === "ru" ? RU_WEIGHT : "Weight"}
                </span>
                <input
                  inputMode="numeric"
                  value={chat.bodyWeightKg}
                  onChange={(event) => chat.setBodyWeightKg(event.currentTarget.value)}
                  disabled={isEditorLocked}
                  placeholder={locale === "ru" ? "78 кг" : "78 kg"}
                  className="h-11 w-full border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                />
              </label>
              <label className="flex h-11 items-center gap-3 border border-slate-200 px-3 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={chat.autoGenerate}
                  onChange={(event) => chat.setAutoGenerate(event.currentTarget.checked)}
                  disabled={chat.isGenerationActionLocked || isEditorLocked}
                  className="h-4 w-4 accent-slate-900"
                />
                <span className={chat.isGenerationActionLocked || isEditorLocked ? "text-slate-400" : undefined}>
                  {locale === "ru" ? RU_GENERATE_IMAGE : "Generate image"}
                </span>
              </label>
            </div>
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
                loading={chat.isSending}
                onClick={chat.handleSend}
                disabled={isInputLocked}
                className="h-11 w-11 self-end rounded-none bg-slate-900 text-white transition hover:bg-slate-800 disabled:bg-slate-300"
              >
                {chat.isSending ? <Loader size={16} color="white" /> : <IconArrowUp size={18} />}
              </ActionIcon>
            </div>
            {chat.messageCooldownRemainingSeconds > 0 ? (
              <p className="pt-2 text-xs text-slate-500">
                {locale === "ru"
                  ? `Следующее сообщение можно отправить ${formatSecondsLabel(locale, chat.messageCooldownRemainingSeconds)}.`
                  : `You can send the next message ${formatSecondsLabel(locale, chat.messageCooldownRemainingSeconds)}.`}
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
