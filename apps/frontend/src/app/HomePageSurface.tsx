"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";

import { BlogCard } from "@/entities/blog-post/ui/BlogCard";
import { ProjectCardWindow } from "@/entities/project/ui/ProjectCardWindow";
import type { BlogPost, Project, SiteSettings } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { ContactModal } from "@/shared/ui/ContactModal";
import { AboutSection } from "@/widgets/about/ui/AboutSection";
import { Footer } from "@/widgets/footer/ui/Footer";
import { Header } from "@/widgets/header/ui/Header";

const ChatWindow = dynamic(
  () => import("@/features/chat/ui/ChatWindowSimpleSurface").then((module) => module.ChatWindowSimpleSurface),
  {
    ssr: false,
    loading: () => (
      <section className="space-y-6">
        <div className="border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
            <div className="space-y-2">
              <div className="h-4 w-28 animate-pulse bg-slate-200" />
              <div className="h-3 w-48 animate-pulse bg-slate-100" />
            </div>
            <div className="h-7 w-16 animate-pulse bg-emerald-50" />
          </div>
          <div className="h-[480px] animate-pulse bg-slate-50" />
        </div>
      </section>
    )
  }
);

const RU_HERO_TITLE = "\u041b\u044e\u0431\u0438\u043c\u044b\u0435 \u043f\u0440\u043e\u0435\u043a\u0442\u044b";
const RU_HERO_SUBTITLE =
  "\u0418\u0418-\u043f\u043e\u043c\u043e\u0449\u043d\u0438\u043a: \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0430\u044f \u043d\u0435\u0439\u0440\u043e\u043d\u043a\u0430 \u0434\u043b\u044f \u043f\u043e\u043c\u043e\u0449\u0438 \u0432 \u0432\u044b\u0431\u043e\u0440\u0435 \u043e\u0434\u0435\u0436\u0434\u044b";
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
      <div className="page-shell space-y-8 py-6 md:space-y-10 md:py-8">
        <Header email={initialSettings.contact_email} onOpenContact={() => setContactOpened(true)} />

        <section className="space-y-6">
          <div className="space-y-3">
            <h1 className="text-4xl font-semibold tracking-tight text-slate-900 md:text-5xl">
              {locale === "ru" ? RU_HERO_TITLE : "Favorite projects"}
            </h1>
            <p className="font-display-italic max-w-3xl text-base leading-7 text-slate-600 md:text-lg">
              {locale === "ru"
                ? RU_HERO_SUBTITLE
                : "AI assistant: a local neural network for helping with outfit selection"}
            </p>
          </div>
          <ChatWindow settings={initialSettings} />
        </section>

        {initialProjects.map((project) => (
          <ProjectCardWindow key={project.id} project={project} locale={locale} />
        ))}

        <section className="space-y-6">
          <div className="space-y-6">
            {initialPosts.map((post) => (
              <BlogCard key={post.id} post={post} locale={locale} />
            ))}
          </div>
          <Link
            href="/blog"
            className="inline-flex rounded-full border border-slate-300 px-5 py-3 text-sm font-medium text-slate-900 transition hover:border-slate-400"
          >
            {locale === "ru" ? RU_ALL_BLOG_POSTS : "All blog posts"}
          </Link>
        </section>

        <section>
          <AboutSection settings={initialSettings} locale={locale} />
        </section>
      </div>
      <div className="page-shell">
        <Footer settings={initialSettings} />
      </div>
      <ContactModal opened={contactOpened} onClose={() => setContactOpened(false)} />
    </>
  );
}
