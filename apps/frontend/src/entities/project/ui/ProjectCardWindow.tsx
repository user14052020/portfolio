import Link from "next/link";

import type { Locale, Project } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function ProjectCardWindow({ project, locale }: { project: Project; locale: Locale }) {
  return (
    <WindowFrame title={pickLocalized(project, "title", locale)} subtitle={project.stack.join(" / ")}>
      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="overflow-hidden rounded-[22px] border border-slate-200/70 bg-slate-950">
          {project.preview_video_url ? (
            <video
              className="h-full min-h-[280px] w-full object-cover"
              src={project.preview_video_url}
              autoPlay
              muted
              loop
              playsInline
            />
          ) : (
            <div
              className="min-h-[280px] w-full bg-cover bg-center"
              style={{ backgroundImage: `url(${project.cover_image})` }}
            />
          )}
        </div>
        <div className="space-y-4">
          <h3 className="text-2xl font-semibold text-slate-900">{pickLocalized(project, "title", locale)}</h3>
          <p className="text-sm leading-7 text-slate-600">{pickLocalized(project, "summary", locale)}</p>
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
          <Link
            href={`/projects/${project.slug}`}
            className="inline-flex rounded-full bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            {locale === "ru" ? "Открыть проект" : "Open project"}
          </Link>
        </div>
      </div>
    </WindowFrame>
  );
}

