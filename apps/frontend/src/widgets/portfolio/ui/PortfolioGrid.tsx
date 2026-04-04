"use client";

import type { Locale, Project } from "@/shared/api/types";
import { SectionTitle } from "@/shared/ui/SectionTitle";
import { ProjectCardWindow } from "@/entities/project/ui/ProjectCardWindow";

export function PortfolioGrid({
  projects,
  locale
}: {
  projects: Project[];
  locale: Locale;
}) {
  return (
    <section id="projects" className="space-y-8">
      <SectionTitle
        eyebrow="Portfolio"
        title={locale === "ru" ? "Избранные работы" : "Selected work"}
        subtitle={
          locale === "ru"
            ? "Кейсы оформлены как рабочие окна creative toolset."
            : "Projects are displayed as open windows from a creative toolset."
        }
      />
      <div className="grid gap-6">
        {projects.map((project) => (
          <ProjectCardWindow key={project.id} project={project} locale={locale} />
        ))}
      </div>
    </section>
  );
}

