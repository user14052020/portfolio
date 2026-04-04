"use client";

import Link from "next/link";

import type { Project } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { ThreeScenePlaceholder } from "@/shared/ui/ThreeScenePlaceholder";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function ProjectDetailPage({ project }: { project: Project }) {
  const { locale, t } = useI18n();
  const galleryItems =
    project.media_items.length > 0
      ? project.media_items
      : project.cover_image
        ? [{ id: 0, asset_type: "image" as const, url: project.cover_image }]
        : [];

  return (
    <div className="page-shell space-y-8 py-10">
      <WindowFrame title={pickLocalized(project, "title", locale)} subtitle={project.stack.join(" / ")}>
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-5">
            <h1 className="text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
              {pickLocalized(project, "title", locale)}
            </h1>
            <p className="text-lg leading-8 text-slate-600">{pickLocalized(project, "description", locale)}</p>
            <div className="flex flex-wrap gap-2">
              {project.stack.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs text-slate-600"
                >
                  {item}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              {project.live_url ? (
                <Link
                  href={project.live_url}
                  className="rounded-full bg-slate-900 px-5 py-3 text-sm font-medium text-white"
                >
                  {t("live")}
                </Link>
              ) : null}
              {project.repository_url ? (
                <Link
                  href={project.repository_url}
                  className="rounded-full border border-slate-300 px-5 py-3 text-sm font-medium text-slate-900"
                >
                  {t("repository")}
                </Link>
              ) : null}
            </div>
          </div>
          <ThreeScenePlaceholder
            title="Project-specific 3D block"
            sceneKey={project.page_scene_key ?? "project-scene"}
            accent="#8fae98"
          />
        </div>
      </WindowFrame>

      <WindowFrame title={locale === "ru" ? "Галерея" : "Gallery"} subtitle={project.slug}>
        <div className="grid gap-4 md:grid-cols-2">
          {galleryItems.map((item) => (
              <div key={item.id} className="overflow-hidden rounded-[22px] border border-slate-200/70 bg-slate-950">
                {item.asset_type === "video" ? (
                  <video src={item.url ?? undefined} className="h-[320px] w-full object-cover" autoPlay loop muted playsInline />
                ) : (
                  <div className="h-[320px] w-full bg-cover bg-center" style={{ backgroundImage: `url(${item.url})` }} />
                )}
              </div>
            ))}
        </div>
      </WindowFrame>
    </div>
  );
}
