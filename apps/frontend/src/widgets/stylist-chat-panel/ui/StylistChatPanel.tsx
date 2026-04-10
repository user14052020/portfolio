"use client";

import { ActionIcon } from "@mantine/core";
import { IconArrowUp } from "@tabler/icons-react";
import { useLayoutEffect, useRef } from "react";

import { UploadArea } from "@/features/chat/ui/UploadArea";
import { getScenarioPlaceholder } from "@/processes/stylist-chat/lib";
import { useStylistChatProcess } from "@/processes/stylist-chat/model/useStylistChatProcess";
import type { SiteSettings } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { ChatThread } from "@/widgets/chat-thread/ui/ChatThread";
import { GarmentGenerationStatus } from "@/widgets/garment-generation-status/ui/GarmentGenerationStatus";
import { GarmentMatchingEntry } from "@/widgets/garment-matching-entry/ui/GarmentMatchingEntry";
import { GarmentMatchingFollowup } from "@/widgets/garment-matching-followup/ui/GarmentMatchingFollowup";
import { OccasionEntry } from "@/widgets/occasion-entry/ui/OccasionEntry";
import { OccasionFollowup } from "@/widgets/occasion-followup/ui/OccasionFollowup";
import { OccasionGenerationStatus } from "@/widgets/occasion-generation-status/ui/OccasionGenerationStatus";

const RU_ASSISTANT_FALLBACK = "Валентин";
const RU_ONLINE = "онлайн";
const RU_GENERATING = "генерация";
const RU_OFFLINE = "офлайн";
const RU_CHAT_SUBTITLE =
  "Тонкий UI сценарного стилиста: команда, follow-up и генерация управляются backend-контекстом.";
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
  const chat = useStylistChatProcess(locale);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const prependScrollStateRef = useRef<{ scrollHeight: number; scrollTop: number } | null>(null);
  const hasInitialScrollRef = useRef(false);
  const shouldStickToBottomRef = useRef(true);
  const previousMessageCountRef = useRef(chat.messages.length);

  const assistantName =
    (locale === "ru" ? settings.assistant_name_ru : settings.assistant_name_en) ||
    (locale === "ru" ? RU_ASSISTANT_FALLBACK : "Jose");
  const assistantLabel = assistantName;
  const chatSubtitle =
    locale === "ru"
      ? RU_CHAT_SUBTITLE
      : "Thin UI for a scenario-driven stylist: commands, follow-ups, and generation are all backend-driven.";
  const chatWelcome =
    locale === "ru"
      ? "Начните с quick action или отправьте обычное сообщение. Frontend не угадывает сценарий сам: он только передаёт команду, сообщение и прикреплённый asset."
      : "Start with a quick action or send a regular message. The frontend does not guess the scenario: it only passes the command, the message, and the attached asset.";
  const chatPlaceholder = getScenarioPlaceholder(chat.scenarioContext, locale);
  const statusBadge = getStatusBadge(locale, chat.chatAvailability, isGenerationActive(chat.activeJob?.status));
  const scenarioLabel =
    chat.scenarioContext.commandName ??
    (chat.scenarioContext.activeMode === "general_advice" ? null : chat.scenarioContext.activeMode);
  const isOccasionScenario =
    chat.scenarioContext.activeMode === "occasion_outfit" ||
    chat.scenarioContext.commandName === "occasion_outfit";

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
          <ChatThread
            messages={chat.messages}
            locale={locale}
            assistantLabel={assistantLabel}
            welcomeText={chatWelcome}
            errorMessage={chat.errorMessage}
            isLoadingOlderHistory={chat.isLoadingOlderHistory}
            isSending={chat.isSending}
          />
        </div>

        <div className="border-t border-slate-200 px-4 py-4">
          {isOccasionScenario ? (
            <OccasionGenerationStatus
              job={chat.activeJob}
              locale={locale}
              isRefreshing={chat.isRefreshingQueue}
              queueRefreshRemainingSeconds={chat.queueRefreshRemainingSeconds}
              onRefresh={() => void chat.refreshGenerationStatus()}
            />
          ) : (
            <GarmentGenerationStatus
              job={chat.activeJob}
              locale={locale}
              isRefreshing={chat.isRefreshingQueue}
              queueRefreshRemainingSeconds={chat.queueRefreshRemainingSeconds}
              onRefresh={() => void chat.refreshGenerationStatus()}
            />
          )}

          <div className="mb-3 space-y-3">
            {isOccasionScenario ? (
              <OccasionEntry
                locale={locale}
                disabled={chat.isGenerationActionLocked}
                activeCommandName={chat.scenarioContext.commandName}
                onAction={(actionId) => void chat.runQuickAction(actionId)}
              />
            ) : (
              <GarmentMatchingEntry
                locale={locale}
                disabled={chat.isGenerationActionLocked}
                activeCommandName={chat.scenarioContext.commandName}
                onAction={(actionId) => void chat.runQuickAction(actionId)}
              />
            )}

            {chat.scenarioContext.pendingClarificationText &&
            chat.scenarioContext.activeMode === "garment_matching" ? (
              <GarmentMatchingFollowup
                locale={locale}
                pendingClarificationText={chat.scenarioContext.pendingClarificationText}
              />
            ) : chat.scenarioContext.pendingClarificationText &&
              chat.scenarioContext.activeMode === "occasion_outfit" ? (
              <OccasionFollowup
                locale={locale}
                pendingClarificationText={chat.scenarioContext.pendingClarificationText}
              />
            ) : scenarioLabel || chat.scenarioContext.pendingClarification ? (
              <div className="border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                {scenarioLabel ? (
                  <p className="font-medium">
                    {locale === "ru" ? "Активный сценарий" : "Active scenario"}: {scenarioLabel}
                  </p>
                ) : null}
                {chat.scenarioContext.pendingClarificationText ? (
                  <p className="mt-1 leading-6">{chat.scenarioContext.pendingClarificationText}</p>
                ) : null}
              </div>
            ) : null}

            {chat.uploadedAsset ? (
              <div className="flex items-center justify-between border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
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

          <div className="border border-slate-200 bg-white px-3 py-2">
            <div className="flex items-end gap-3">
              <UploadArea
                onSelect={(file) => void chat.handleAttachAsset(file)}
                isLoading={chat.isUploading}
                filename={chat.uploadedAsset?.original_filename}
                disabled={!chat.scenarioContext.canAttachAsset || chat.isEditorLocked}
              />
              <textarea
                ref={textareaRef}
                value={chat.input}
                disabled={chat.isEditorLocked || !chat.scenarioContext.canSendFreeformMessage}
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
              <ActionIcon
                radius={0}
                size="xl"
                color="dark"
                onClick={() => void chat.sendComposerMessage()}
                disabled={chat.isSendLocked}
                className="h-11 w-11 self-end rounded-none bg-slate-900 text-white transition hover:bg-slate-800 disabled:bg-slate-300"
              >
                <IconArrowUp size={18} />
              </ActionIcon>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
