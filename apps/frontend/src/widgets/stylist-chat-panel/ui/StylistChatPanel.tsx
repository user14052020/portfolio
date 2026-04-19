"use client";

import { useLayoutEffect, useRef } from "react";

import { UploadArea } from "@/features/chat/ui/UploadArea";
import { ChatCooldownSendControl } from "@/features/chat-cooldown/ui/ChatCooldownSendControl";
import { GenerationStatusRail } from "@/features/chat/ui/GenerationStatusRail";
import { getQuickActionDefinitions } from "@/features/run-chat-command/model/runChatCommand";
import { getScenarioPlaceholder } from "@/processes/stylist-chat/model/lib";
import { useStylistChatProcess } from "@/processes/stylist-chat/model/useStylistChatProcess";
import type { SiteSettings } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { InputSurface } from "@/shared/ui/InputSurface";
import { SoftButton } from "@/shared/ui/SoftButton";
import { ChatThread } from "@/widgets/chat-thread/ui/ChatThread";

const RU_ASSISTANT_FALLBACK = "Валентин";
const RU_ONLINE = "онлайн";
const RU_GENERATING = "генерация";
const RU_OFFLINE = "офлайн";
const RU_CHAT_SUBTITLE =
  "Text-first стилист: визуализация запускается только по кнопке, явному запросу или подтверждённому CTA.";
const TOP_HISTORY_LOAD_THRESHOLD_PX = 48;

function isGenerationActive(status: string | undefined) {
  return status === "pending" || status === "queued" || status === "running";
}

function isNearBottom(container: HTMLDivElement) {
  return container.scrollHeight - container.scrollTop - container.clientHeight <= 72;
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

export function StylistChatPanel({ settings }: { settings: SiteSettings }) {
  const { locale } = useI18n();
  const chat = useStylistChatProcess(locale, {
    messageCooldownSeconds: settings.message_cooldown_seconds,
    tryOtherStyleCooldownSeconds: settings.try_other_style_cooldown_seconds,
  });
  const quickActions = getQuickActionDefinitions(locale);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const prependScrollStateRef = useRef<{ scrollHeight: number; scrollTop: number } | null>(null);
  const hasInitialScrollRef = useRef(false);
  const shouldStickToBottomRef = useRef(true);
  const previousMessageCountRef = useRef(chat.messages.length);

  const assistantName =
    (locale === "ru" ? settings.assistant_name_ru : settings.assistant_name_en) ||
    (locale === "ru" ? RU_ASSISTANT_FALLBACK : "Jose");
  const chatSubtitle =
    locale === "ru"
      ? RU_CHAT_SUBTITLE
      : "Text-first stylist: generation only starts from the style button, an explicit visual request, or a confirmed CTA.";
  const chatWelcome =
    locale === "ru"
      ? "Начните с кнопки «Попробовать другой стиль» или просто опишите вещь, событие или вопрос по стилю. Если визуализация уместна, я предложу её отдельной CTA-кнопкой."
      : "Start with “Try another style” or just describe the garment, occasion, or styling question. If visualization makes sense, I will offer it as a separate CTA.";
  const chatPlaceholder = getScenarioPlaceholder(chat.scenarioContext, locale);
  const statusBadge = getStatusBadge(locale, chat.chatAvailability, isGenerationActive(chat.activeJob?.status));
  const interactionCooldownReason = chat.isChatCooldownActive
    ? chat.chatCooldownActionType === "try_other_style"
      ? locale === "ru"
        ? "Чат временно заблокирован после выбора нового стиля"
        : "The chat is temporarily locked after trying another style"
      : locale === "ru"
        ? "Чат временно заблокирован после отправки сообщения"
        : "The chat is temporarily locked after sending a message"
    : null;
  const sendControlDisabledReason = chat.isChatCooldownActive
    ? chat.chatCooldownActionType === "try_other_style"
      ? locale === "ru"
        ? "Повторный запуск нового стиля временно заблокирован"
        : "Trying another style is temporarily locked"
      : locale === "ru"
        ? "Отправка сообщений временно заблокирована"
        : "Sending messages is temporarily locked"
    : null;
  const sendControlHardDisabled =
    chat.isEditorLocked || !chat.scenarioContext.canSendFreeformMessage || (!chat.isChatCooldownActive && !chat.input.trim() && !chat.uploadedAsset);
  const areChatInteractionsBlocked = chat.isChatCooldownActive;
  const areQuickActionsDisabled = chat.isGenerationActionLocked || areChatInteractionsBlocked;
  const canShowVisualizationCta =
    chat.visualizationOffer.canOfferVisualization && !chat.scenarioContext.pendingClarification;
  const isVisualizationCtaDisabled = chat.isGenerationActionLocked || areChatInteractionsBlocked;

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
      !hasInitialScrollRef.current || (messageCountIncreased && shouldStickToBottomRef.current) || chat.isSending;

    if (shouldScrollToBottom) {
      container.scrollTop = container.scrollHeight;
      shouldStickToBottomRef.current = true;
      hasInitialScrollRef.current = true;
    }

    previousMessageCountRef.current = chat.messages.length;
  }, [chat.messages.length, chat.isSending, chat.activeJob?.result_url]);

  return (
    <section className="space-y-6">
      <div className="overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-[0_24px_64px_rgba(15,23,42,0.08)]">
        <div className="flex items-center justify-between border-b border-slate-200 bg-[linear-gradient(180deg,rgba(248,250,252,0.94),rgba(255,255,255,0.98))] px-6 py-5">
          <div>
            <p className="font-display text-sm text-slate-900">{assistantName}</p>
            <p className="text-sm text-slate-500">{chatSubtitle}</p>
          </div>
          <div className={statusBadge.className}>{statusBadge.label}</div>
        </div>

        <div
          ref={scrollContainerRef}
          className="h-[480px] overflow-y-auto bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] px-6 py-6"
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
          <ChatThread
            messages={chat.messages}
            locale={locale}
            assistantLabel={assistantName}
            welcomeText={chatWelcome}
            errorMessage={chat.errorMessage}
            isLoadingOlderHistory={chat.isLoadingOlderHistory}
            isSending={chat.isSending}
          />
        </div>

        <div className="border-t border-slate-200 px-4 py-4">
          <GenerationStatusRail
            job={chat.activeJob}
            locale={locale}
            isPreparing={chat.isSending && !chat.activeJob}
          />

          <div className="mb-3 space-y-3">
            <div className="flex flex-wrap gap-2">
              {quickActions.map((action) => (
                <SoftButton
                  key={action.id}
                  onClick={() => void chat.runQuickAction(action.id)}
                  disabled={areQuickActionsDisabled}
                  title={interactionCooldownReason ?? undefined}
                  tone="neutral"
                  shape="pill"
                >
                  {action.label}
                </SoftButton>
              ))}
            </div>

            {canShowVisualizationCta ? (
              <SoftButton
                onClick={() => void chat.requestVisualization()}
                disabled={isVisualizationCtaDisabled}
                title={interactionCooldownReason ?? undefined}
                tone="accent"
                shape="surface"
                fullWidth
                align="left"
                className="font-medium"
              >
                {chat.visualizationOffer.ctaText ?? (locale === "ru" ? "Собрать flat lay референс?" : "Build a flat lay reference?")}
              </SoftButton>
            ) : null}

            {chat.scenarioContext.pendingClarificationText ? (
              <div className="rounded-[24px] border border-slate-200 bg-slate-50/90 px-4 py-3 text-sm text-slate-700 shadow-sm">
                <p className="font-medium">
                  {locale === "ru" ? "Нужно уточнение" : "Need a follow-up"}
                </p>
                <p className="mt-1 leading-6">{chat.scenarioContext.pendingClarificationText}</p>
              </div>
            ) : null}

            {chat.uploadedAsset ? (
              <div className="flex items-center justify-between rounded-[24px] border border-slate-200 bg-white/90 px-4 py-3 text-sm text-slate-700 shadow-sm">
                <span>
                  {locale === "ru" ? "Прикреплённый asset" : "Attached asset"}: {chat.uploadedAsset.original_filename}
                </span>
                <button
                  type="button"
                  onClick={chat.clearUploadedAsset}
                  className="text-xs uppercase tracking-[0.18em] text-slate-500 transition hover:text-slate-900"
                >
                  {locale === "ru" ? "убрать" : "remove"}
                </button>
              </div>
            ) : null}
          </div>

          <InputSurface disabled={chat.isEditorLocked || areChatInteractionsBlocked} className="px-3 py-2.5">
            <div className="flex items-end gap-3">
              <UploadArea
                onSelect={(file) => void chat.handleAttachAsset(file)}
                isLoading={chat.isUploading}
                filename={chat.uploadedAsset?.original_filename}
                disabled={!chat.scenarioContext.canAttachAsset || chat.isEditorLocked || areChatInteractionsBlocked}
              />
              <textarea
                ref={textareaRef}
                value={chat.input}
                disabled={chat.isEditorLocked || !chat.scenarioContext.canSendFreeformMessage || areChatInteractionsBlocked}
                title={interactionCooldownReason ?? undefined}
                onChange={(event) => chat.setInput(event.currentTarget.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    if (!chat.isSendLocked) {
                      void chat.sendComposerMessage();
                    }
                  }
                }}
                rows={1}
                placeholder={chatPlaceholder}
                className="min-h-[44px] flex-1 resize-none overflow-hidden border-0 bg-transparent py-[10px] text-base leading-6 text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:text-slate-400"
              />
              <ChatCooldownSendControl
                isLocked={chat.isChatCooldownActive}
                secondsRemaining={chat.chatCooldownRemainingSeconds}
                cooldownSeconds={chat.chatCooldownSeconds}
                onSubmit={() => void chat.sendComposerMessage()}
                disabled={sendControlHardDisabled}
                disabledReason={sendControlDisabledReason}
                variant="dark"
              />
            </div>
          </InputSurface>
        </div>
      </div>
    </section>
  );
}
