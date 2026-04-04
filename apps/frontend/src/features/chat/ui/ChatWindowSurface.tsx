"use client";

import { ActionIcon, Loader } from "@mantine/core";
import { IconArrowUp } from "@tabler/icons-react";
import { useLayoutEffect, useRef } from "react";

import { GenerationResultSurface } from "@/entities/generation-job/ui/GenerationResultSurface";
import { useStylistChat } from "@/features/chat/model/useStylistChat";
import { UploadArea } from "@/features/chat/ui/UploadArea";
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
const RU_GENDER = "\u041f\u043e\u043b";
const RU_HEIGHT = "\u0420\u043e\u0441\u0442";
const RU_WEIGHT = "\u0412\u0435\u0441";
const RU_GENERATE_IMAGE = "\u0413\u0435\u043d\u0435\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0438\u0437\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435";
const RU_MALE = "\u041c\u0443\u0436\u0447\u0438\u043d\u0430";
const RU_FEMALE = "\u0416\u0435\u043d\u0449\u0438\u043d\u0430";
const RU_PROFILE_HINT =
  "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u043f\u043e\u043b, \u0440\u043e\u0441\u0442 \u0438 \u0432\u0435\u0441, \u0447\u0442\u043e\u0431\u044b \u0441\u0442\u0438\u043b\u0438\u0441\u0442 \u0442\u043e\u0447\u043d\u0435\u0435 \u0443\u0447\u0435\u043b \u043f\u0440\u043e\u043f\u043e\u0440\u0446\u0438\u0438.";

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

function formatRemainingTime(milliseconds: number) {
  const totalSeconds = Math.max(0, Math.ceil(milliseconds / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function CooldownIndicator({
  remainingMs,
  totalMs
}: {
  remainingMs: number;
  totalMs: number;
}) {
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(1, Math.max(0, (totalMs - remainingMs) / totalMs));
  const dashOffset = circumference * (1 - progress);

  return (
    <div className="relative flex h-11 w-11 items-center justify-center self-end">
      <svg className="h-11 w-11 -rotate-90" viewBox="0 0 44 44" aria-hidden="true">
        <circle cx="22" cy="22" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="2" />
        <circle
          cx="22"
          cy="22"
          r={radius}
          fill="none"
          stroke="#0f172a"
          strokeWidth="2"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-[9px] font-medium text-slate-700">{formatRemainingTime(remainingMs)}</span>
    </div>
  );
}

export function ChatWindowSurface({ settings }: { settings: SiteSettings }) {
  const { locale } = useI18n();
  const chat = useStylistChat(locale);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
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
    if (chat.isHistoryLoading) {
      return;
    }
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [chat.isHistoryLoading, chat.messages.length, chat.isGenerationPreparing, chat.activeJob?.updated_at]);

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
            <div className="border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
              {locale === "ru" ? RU_ONLINE : "online"}
            </div>
          </div>
        </div>
        <div className="h-[480px] overflow-y-auto px-5 py-6">
          {chat.isHistoryLoading ? (
            <div className="flex h-full items-center justify-center">
              <Loader size="sm" color="dark" />
            </div>
          ) : (
            <div className="space-y-6">
              <div className="space-y-6">
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
                  chat.messages.map((message) => (
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
                        <div
                          className={
                            message.role === "assistant"
                              ? "inline-block w-fit max-w-[620px] border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm leading-7 text-slate-700"
                              : "inline-block w-fit max-w-[620px] bg-slate-900 px-4 py-3 text-left text-sm leading-7 text-white"
                          }
                        >
                          {message.content}
                        </div>
                      </div>

                      {message.role === "assistant" && message.generation_job ? (
                        <GenerationResultSurface
                          job={message.generation_job}
                          locale={locale}
                          assistantLabel={assistantLabel}
                          isPreparing={false}
                        />
                      ) : null}
                    </div>
                  ))
                )}
                <GenerationResultSurface
                  job={null}
                  locale={locale}
                  assistantLabel={assistantLabel}
                  isPreparing={chat.isGenerationPreparing}
                />
                <div ref={bottomRef} />
              </div>
            </div>
          )}
        </div>
        <div className="border-t border-slate-200 px-4 py-4">
          <div className="border border-slate-200 bg-white px-3 py-2">
            <div className="mb-3 grid gap-3 md:grid-cols-[1.2fr_1fr_1fr_auto]">
              <label className="space-y-1">
                <span className="text-[11px] font-medium uppercase tracking-[0.2em] text-slate-500">
                  {locale === "ru" ? RU_GENDER : "Gender"}
                </span>
                <select
                  value={chat.profileGender}
                  onChange={(event) => chat.setProfileGender(event.currentTarget.value)}
                  className="h-11 w-full border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-slate-400"
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
                  placeholder={locale === "ru" ? "182 см" : "182 cm"}
                  className="h-11 w-full border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400"
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
                  placeholder={locale === "ru" ? "78 кг" : "78 kg"}
                  className="h-11 w-full border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-slate-400"
                />
              </label>
              <label className="flex h-11 items-center gap-3 border border-slate-200 px-3 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={chat.autoGenerate}
                  onChange={(event) => chat.setAutoGenerate(event.currentTarget.checked)}
                  className="h-4 w-4 accent-slate-900"
                />
                <span>{locale === "ru" ? RU_GENERATE_IMAGE : "Generate image"}</span>
              </label>
            </div>
            <div className="flex items-end gap-3">
              <UploadArea
                onSelect={chat.handleUpload}
                isLoading={chat.isUploading}
                filename={chat.uploadedAsset?.original_filename}
              />
              <textarea
                ref={textareaRef}
                value={chat.input}
                onChange={(event) => chat.setInput(event.currentTarget.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    void chat.handleSend();
                  }
                }}
                rows={1}
                placeholder={chatPlaceholder}
                className="min-h-[44px] flex-1 resize-none overflow-hidden border-0 bg-transparent py-[10px] text-base leading-6 text-slate-800 outline-none placeholder:text-slate-400"
              />
              {chat.cooldownRemainingMs > 0 ? (
                <CooldownIndicator
                  remainingMs={chat.cooldownRemainingMs}
                  totalMs={chat.messageCooldownMs}
                />
              ) : (
                <ActionIcon
                  radius={0}
                  size="xl"
                  color="dark"
                  loading={chat.isSending}
                  onClick={chat.handleSend}
                  disabled={chat.isSending || chat.isUploading}
                  className="h-11 w-11 self-end rounded-none bg-slate-900 text-white transition hover:bg-slate-800 disabled:bg-slate-300"
                >
                  {chat.isSending ? <Loader size={16} color="white" /> : <IconArrowUp size={18} />}
                </ActionIcon>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
