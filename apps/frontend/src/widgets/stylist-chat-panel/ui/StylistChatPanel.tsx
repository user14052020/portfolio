"use client";

import { useLayoutEffect, useRef } from "react";

import { getQuickActionDefinitions } from "@/features/run-chat-command/model/runChatCommand";
import { getScenarioPlaceholder } from "@/processes/stylist-chat/model/lib";
import { useStylistChatProcess } from "@/processes/stylist-chat/model/useStylistChatProcess";
import type { SiteSettings } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { ChatThread } from "@/widgets/chat-thread/ui/ChatThread";
import { ChatAssistantHeader } from "@/widgets/stylist-chat-panel/ui/ChatAssistantHeader";
import { ChatAttachedAssetChip } from "@/widgets/stylist-chat-panel/ui/ChatAttachedAssetChip";
import { ChatClarificationPanel } from "@/widgets/stylist-chat-panel/ui/ChatClarificationPanel";
import { ChatComposerDock } from "@/widgets/stylist-chat-panel/ui/ChatComposerDock";
import { ChatConversationSurface } from "@/widgets/stylist-chat-panel/ui/ChatConversationSurface";
import { ChatGenerationDock } from "@/widgets/stylist-chat-panel/ui/ChatGenerationDock";
import { ChatQuickActionsBar } from "@/widgets/stylist-chat-panel/ui/ChatQuickActionsBar";

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
    return {
      label: locale === "ru" ? RU_OFFLINE : "offline",
      tone: "offline" as const,
    };
  }

  if (isGenerating) {
    return {
      label: locale === "ru" ? RU_GENERATING : "generating",
      tone: "generating" as const,
    };
  }

  return {
    label: locale === "ru" ? RU_ONLINE : "online",
    tone: "online" as const,
  };
}

function getModeLabel(locale: "ru" | "en", mode: string) {
  if (locale === "ru") {
    if (mode === "style_exploration") {
      return "режим: стиль";
    }
    if (mode === "garment_matching") {
      return "режим: вещь";
    }
    if (mode === "occasion_outfit") {
      return "режим: повод";
    }
    return "режим: совет";
  }

  if (mode === "style_exploration") {
    return "mode: style";
  }
  if (mode === "garment_matching") {
    return "mode: garment";
  }
  if (mode === "occasion_outfit") {
    return "mode: occasion";
  }
  return "mode: advice";
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
    const nextHeight = Math.min(Math.max(textarea.scrollHeight, 48), 240);
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
      <div className="overflow-hidden rounded-[36px] border border-white/75 bg-white shadow-[var(--shadow-soft-xl)]">
        <ChatAssistantHeader
          assistantName={assistantName}
          subtitle={chatSubtitle}
          statusLabel={statusBadge.label}
          statusTone={statusBadge.tone}
          modeLabel={getModeLabel(locale, chat.scenarioContext.activeMode)}
        />

        <ChatConversationSurface
          ref={scrollContainerRef}
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
        </ChatConversationSurface>

        <div className="border-t border-[var(--border-soft)] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(247,245,240,0.88))] px-4 py-4">
          <ChatGenerationDock
            job={chat.activeJob}
            locale={locale}
            isPreparing={chat.isSending && !chat.activeJob}
          />

          <div className="mb-3 space-y-3">
            <ChatQuickActionsBar
              quickActions={quickActions}
              locale={locale}
              disabled={areQuickActionsDisabled}
              disabledTitle={interactionCooldownReason}
              canShowVisualizationCta={canShowVisualizationCta}
              visualizationCtaText={chat.visualizationOffer.ctaText}
              isVisualizationCtaDisabled={isVisualizationCtaDisabled}
              onRunQuickAction={(actionId) => void chat.runQuickAction(actionId)}
              onRequestVisualization={() => void chat.requestVisualization()}
            />

            {chat.scenarioContext.pendingClarificationText ? (
              <ChatClarificationPanel
                locale={locale}
                text={chat.scenarioContext.pendingClarificationText}
                onSuggestionSelect={chat.setInput}
              />
            ) : null}

            {chat.uploadedAsset ? (
              <ChatAttachedAssetChip
                locale={locale}
                filename={chat.uploadedAsset.original_filename}
                onRemove={chat.clearUploadedAsset}
              />
            ) : null}
          </div>

          <ChatComposerDock
            textareaRef={textareaRef}
            input={chat.input}
            placeholder={chatPlaceholder}
            title={interactionCooldownReason ?? undefined}
            disabled={chat.isEditorLocked || areChatInteractionsBlocked}
            textareaDisabled={chat.isEditorLocked || !chat.scenarioContext.canSendFreeformMessage || areChatInteractionsBlocked}
            isSendLocked={sendControlHardDisabled}
            isCooldownActive={chat.isChatCooldownActive}
            cooldownRemainingSeconds={chat.chatCooldownRemainingSeconds}
            cooldownSeconds={chat.chatCooldownSeconds}
            sendControlDisabledReason={sendControlDisabledReason}
            onInputChange={chat.setInput}
            onSubmit={() => void chat.sendComposerMessage()}
          />
        </div>
      </div>
    </section>
  );
}
