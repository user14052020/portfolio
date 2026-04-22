import Link from "next/link";

import type { Locale, Project } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { cn } from "@/shared/lib/cn";
import { PillBadge } from "@/shared/ui/PillBadge";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function ProjectCardWindow({
  project,
  locale,
  featured = false,
  reversed = false,
}: {
  project: Project;
  locale: Locale;
  featured?: boolean;
  reversed?: boolean;
}) {
  return (
    <WindowFrame
      title={featured ? (locale === "ru" ? "Главный кейс" : "Featured case") : pickLocalized(project, "title", locale)}
      subtitle={project.stack.join(" / ")}
      variant={featured ? "elevated" : "tinted"}
      decorativeTone={featured ? "sand" : reversed ? "lilac" : "mint"}
      bodyClassName={featured ? "p-4 md:p-5" : undefined}
    >
      <div className={cn("grid gap-6 lg:items-stretch", featured ? "lg:grid-cols-[1.45fr_0.9fr]" : "lg:grid-cols-[1.1fr_0.9fr]")}>
        <div
          className={cn(
            "overflow-hidden rounded-[28px] border border-white/75 bg-slate-950 shadow-[var(--shadow-soft-md)]",
            reversed && "lg:order-2",
          )}
        >
          {project.preview_video_url ? (
            <video
              className={cn("h-full w-full object-cover", featured ? "min-h-[360px]" : "min-h-[280px]")}
              src={project.preview_video_url}
              autoPlay
              muted
              loop
              playsInline
            />
          ) : project.cover_image ? (
            <div
              className={cn("w-full bg-cover bg-center", featured ? "min-h-[360px]" : "min-h-[280px]")}
              style={{ backgroundImage: `url(${project.cover_image})` }}
            />
          ) : (
            <div
              className={cn(
                "flex w-full items-center justify-center bg-[radial-gradient(circle_at_28%_18%,rgba(208,164,109,0.36),transparent_18rem),linear-gradient(135deg,#141416,#2d2a25)] text-sm font-medium text-white/70",
                featured ? "min-h-[360px]" : "min-h-[280px]",
              )}
            >
              {pickLocalized(project, "title", locale)}
            </div>
          )}
        </div>
        <div className="flex flex-col justify-between gap-6 rounded-[28px] bg-white/60 p-5 md:p-6">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <PillBadge tone={featured ? "accent" : "subtle"} size="sm">
                {featured ? (locale === "ru" ? "выбор" : "selected") : "case"}
              </PillBadge>
              {project.is_featured ? (
                <PillBadge tone="mint" size="sm">
                  featured
                </PillBadge>
              ) : null}
            </div>
            <h3 className="text-3xl font-semibold leading-tight tracking-[-0.03em] text-[var(--text-primary)]">
              {pickLocalized(project, "title", locale)}
            </h3>
            <p className="text-sm leading-7 text-[var(--text-secondary)]">{pickLocalized(project, "summary", locale)}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {project.stack.map((item) => (
              <PillBadge key={item} tone="neutral" size="sm" className="normal-case tracking-normal">
                {item}
              </PillBadge>
            ))}
          </div>
          <Link
            href={`/projects/${project.slug}`}
            className="inline-flex w-fit rounded-[var(--radius-pill)] bg-[var(--surface-ink)] px-5 py-3 text-sm font-medium text-white transition hover:bg-black"
          >
            {locale === "ru" ? "Открыть проект" : "Open project"}
          </Link>
        </div>
      </div>
    </WindowFrame>
  );
}
