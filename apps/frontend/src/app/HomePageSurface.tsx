"use client";

import dynamic from "next/dynamic";

import type { Project, SiteSettings } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { HomeShowcase } from "@/widgets/home-showcase/ui/HomeShowcase";

const ChatWindow = dynamic(
  () => import("@/features/chat/ui/ChatWindowSimpleSurface").then((module) => module.ChatWindowSimpleSurface),
  {
    ssr: false,
    loading: () => (
      <div className="min-h-[560px] rounded-lg border border-black/10 bg-white p-6">
        <div className="h-4 w-32 animate-pulse rounded bg-slate-200" />
        <div className="mt-4 h-[480px] animate-pulse rounded bg-slate-100" />
      </div>
    ),
  }
);

export function HomePageSurface({
  initialSettings,
  initialProjects,
}: {
  initialSettings: SiteSettings;
  initialProjects: Project[];
}) {
  const { locale, setLocale } = useI18n();

  return (
    <HomeShowcase
      settings={initialSettings}
      projects={initialProjects}
      locale={locale}
      onLocaleChange={setLocale}
      chatSlot={initialSettings.chat_bot_enabled ? <ChatWindow settings={initialSettings} /> : null}
    />
  );
}
