"use client";

import type { BlogPost } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { RichContent } from "@/shared/ui/RichContent";
import { ThreeScenePlaceholder } from "@/shared/ui/ThreeScenePlaceholder";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function BlogPostPage({ post }: { post: BlogPost }) {
  const { locale } = useI18n();

  return (
    <div className="page-shell space-y-8 py-10">
      <WindowFrame title={post.post_type.toUpperCase()} subtitle={post.category ? pickLocalized(post.category, "name", locale) : undefined}>
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-5">
            <h1 className="text-4xl font-semibold tracking-tight text-slate-950 md:text-6xl">
              {pickLocalized(post, "title", locale)}
            </h1>
            <p className="text-lg leading-8 text-slate-600">{pickLocalized(post, "excerpt", locale)}</p>
            <div className="flex flex-wrap gap-2">
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full border border-slate-200 bg-[#f8f1e8] px-3 py-1 text-xs text-slate-700"
                >
                  #{tag}
                </span>
              ))}
            </div>
          </div>
          <ThreeScenePlaceholder
            title="Post-specific 3D block"
            sceneKey={post.page_scene_key ?? "blog-scene"}
            accent="#b36f4e"
          />
        </div>
      </WindowFrame>

      {post.video_url ? (
        <WindowFrame title={locale === "ru" ? "Видео" : "Video"} subtitle={post.slug}>
          <video className="w-full rounded-[22px] border border-slate-200/70" src={post.video_url} controls playsInline />
        </WindowFrame>
      ) : null}

      <WindowFrame title={locale === "ru" ? "Контент" : "Content"} subtitle={post.slug}>
        <RichContent content={pickLocalized(post, "content", locale)} />
      </WindowFrame>
    </div>
  );
}

