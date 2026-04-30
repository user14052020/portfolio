"use client";

import { useEffect, useState } from "react";

import { BlogCard } from "@/entities/blog-post/ui/BlogCard";
import { SearchAndFilter } from "@/features/content-search/ui/SearchAndFilter";
import { getBlogPosts } from "@/shared/api/browser-client";
import type { BlogPost } from "@/shared/api/types";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { SectionTitle } from "@/shared/ui/SectionTitle";
import { ThreeScenePlaceholder } from "@/shared/ui/ThreeScenePlaceholder";

export default function BlogPage() {
  const { locale, t } = useI18n();
  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const [posts, setPosts] = useState<BlogPost[]>([]);

  useEffect(() => {
    getBlogPosts({ q: query || undefined, postType: type === "all" ? undefined : type }).then(setPosts);
  }, [query, type]);

  return (
    <div className="page-shell space-y-8 py-10">
      <SectionTitle eyebrow="Blog" title={t("blogTitle")} subtitle={t("blogSubtitle")} />
      <ThreeScenePlaceholder title="Blog 3D block" sceneKey="blog-particle-field" accent="#b36f4e" />
      <SearchAndFilter query={query} onQueryChange={setQuery} type={type} onTypeChange={setType} />
      <div className="grid gap-6 lg:grid-cols-2">
        {posts.map((post) => (
          <BlogCard key={post.id} post={post} locale={locale} />
        ))}
      </div>
    </div>
  );
}
