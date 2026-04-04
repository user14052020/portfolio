"use client";

import Link from "next/link";

import type { BlogPost, Locale } from "@/shared/api/types";
import { BlogCard } from "@/entities/blog-post/ui/BlogCard";
import { SectionTitle } from "@/shared/ui/SectionTitle";

export function BlogSection({
  posts,
  locale
}: {
  posts: BlogPost[];
  locale: Locale;
}) {
  return (
    <section id="blog" className="space-y-8">
      <SectionTitle
        eyebrow="Blog"
        title={locale === "ru" ? "Тексты и видеозаметки" : "Writing and video notes"}
        subtitle={
          locale === "ru"
            ? "Архитектура интерфейсов, AI-инструменты и motion-практика."
            : "Interface architecture, AI tooling and motion-driven product practice."
        }
      />
      <div className="space-y-6">
        {posts.map((post) => (
          <BlogCard key={post.id} post={post} locale={locale} />
        ))}
      </div>
      <Link
        href="/blog"
        className="inline-flex rounded-full border border-slate-300 px-5 py-3 text-sm font-medium text-slate-900 transition hover:border-slate-400"
      >
        {locale === "ru" ? "Все записи блога" : "All blog posts"}
      </Link>
    </section>
  );
}
