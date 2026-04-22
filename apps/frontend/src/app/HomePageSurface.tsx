"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";

import { BlogCard } from "@/entities/blog-post/ui/BlogCard";
import { ProjectCardWindow } from "@/entities/project/ui/ProjectCardWindow";
import type { BlogPost, Project, SiteSettings } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { ContactModal } from "@/shared/ui/ContactModal";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import { AboutSection } from "@/widgets/about/ui/AboutSection";
import { Footer } from "@/widgets/footer/ui/Footer";
import { HomeHeroAssistantStage } from "@/widgets/hero/ui/HomeHeroAssistantStage";
import { Header } from "@/widgets/header/ui/Header";

const ChatWindow = dynamic(
  () => import("@/features/chat/ui/ChatWindowSimpleSurface").then((module) => module.ChatWindowSimpleSurface),
  {
    ssr: false,
    loading: () => (
      <SurfaceCard variant="elevated" padding="none" className="min-h-[640px] rounded-[36px]">
        <div className="flex items-center justify-between border-b border-[var(--border-soft)] px-6 py-5">
          <div className="space-y-2">
            <div className="h-4 w-28 animate-pulse rounded-full bg-slate-200" />
            <div className="h-3 w-48 animate-pulse rounded-full bg-slate-100" />
          </div>
          <div className="h-7 w-16 animate-pulse rounded-full bg-emerald-50" />
        </div>
        <div className="h-[560px] animate-pulse bg-[linear-gradient(180deg,#ffffff,#f8fafc)]" />
      </SurfaceCard>
    )
  }
);

const RU_PROJECTS_EYEBROW = "Избранные системы";
const RU_PROJECTS_TITLE = "Проекты как доказательство архитектуры, вкуса и доведения до результата";
const RU_PROJECTS_DESCRIPTION =
  "Кейсы собраны как спокойная витрина: backend, frontend, визуальные пайплайны и AI-инструменты работают вместе, а не живут отдельными слоями.";
const RU_BLOG_EYEBROW = "Заметки";
const RU_BLOG_TITLE = "Пишу о продуктах, AI и визуальном мышлении";
const RU_BLOG_DESCRIPTION = "Редакторский блок без шума: короткий вход в идеи, решения и практику вокруг проекта.";
const RU_ALL_BLOG_POSTS = "\u0412\u0441\u0435 \u0437\u0430\u043f\u0438\u0441\u0438 \u0431\u043b\u043e\u0433\u0430";

export function HomePageSurface({
  initialSettings,
  initialProjects,
  initialPosts
}: {
  initialSettings: SiteSettings;
  initialProjects: Project[];
  initialPosts: BlogPost[];
}) {
  const { locale } = useI18n();
  const [contactOpened, setContactOpened] = useState(false);

  return (
    <>
      <main className="premium-page-backdrop min-h-screen pb-12">
        <div className="page-shell space-y-14 py-5 md:space-y-16 md:py-7">
          <Header email={initialSettings.contact_email} onOpenContact={() => setContactOpened(true)} />

          <HomeHeroAssistantStage
            settings={initialSettings}
            locale={locale}
            onOpenContact={() => setContactOpened(true)}
            projectCount={initialProjects.length}
            postCount={initialPosts.length}
          >
            <ChatWindow settings={initialSettings} />
          </HomeHeroAssistantStage>

          {initialProjects.length > 0 ? (
            <section className="section-spacing space-y-7">
              <SectionHeader
                eyebrow={locale === "ru" ? RU_PROJECTS_EYEBROW : "Selected systems"}
                title={
                  locale === "ru"
                    ? RU_PROJECTS_TITLE
                    : "Projects as proof of architecture, taste, and finished execution"
                }
                description={
                  locale === "ru"
                    ? RU_PROJECTS_DESCRIPTION
                    : "A calmer showcase where backend, frontend, visual pipelines, and AI tools work as one product system."
                }
              />
              <div className="space-y-6">
                {initialProjects.map((project, index) => (
                  <ProjectCardWindow
                    key={project.id}
                    project={project}
                    locale={locale}
                    featured={index === 0}
                    reversed={index % 2 === 1}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {initialPosts.length > 0 ? (
            <section className="section-spacing space-y-7">
              <SectionHeader
                eyebrow={locale === "ru" ? RU_BLOG_EYEBROW : "Writing"}
                title={locale === "ru" ? RU_BLOG_TITLE : "Writing about products, AI, and visual thinking"}
                description={
                  locale === "ru"
                    ? RU_BLOG_DESCRIPTION
                    : "An editorial layer for ideas, implementation notes, and the decisions behind the work."
                }
                action={
                  <Link
                    href="/blog"
                    className="inline-flex rounded-[var(--radius-pill)] border border-transparent bg-[var(--surface-secondary)] px-4 py-2.5 text-sm font-medium text-[var(--text-secondary)] transition hover:bg-white/90 hover:text-[var(--text-primary)]"
                  >
                    {locale === "ru" ? RU_ALL_BLOG_POSTS : "All blog posts"}
                  </Link>
                }
              />
              <div className="grid gap-5 lg:grid-cols-2">
                {initialPosts.map((post) => (
                  <BlogCard key={post.id} post={post} locale={locale} />
                ))}
              </div>
            </section>
          ) : null}

          <section className="section-spacing pt-2">
            <AboutSection settings={initialSettings} locale={locale} />
          </section>
        </div>
        <div className="page-shell">
          <Footer settings={initialSettings} />
        </div>
      </main>
      <ContactModal opened={contactOpened} onClose={() => setContactOpened(false)} />
    </>
  );
}
