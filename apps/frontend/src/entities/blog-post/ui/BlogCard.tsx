import Link from "next/link";

import type { BlogPost, Locale } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function BlogCard({ post, locale }: { post: BlogPost; locale: Locale }) {
  return (
    <WindowFrame title={post.post_type.toUpperCase()} subtitle={post.category ? pickLocalized(post.category, "name", locale) : undefined}>
      <div className="space-y-4">
        {post.cover_image ? (
          <div
            className="h-52 rounded-[20px] border border-slate-200/70 bg-cover bg-center"
            style={{ backgroundImage: `url(${post.cover_image})` }}
          />
        ) : null}
        <div className="flex flex-wrap gap-2">
          {post.tags.map((tag) => (
            <span key={tag} className="rounded-full bg-[#f5ede4] px-3 py-1 text-xs text-slate-700">
              #{tag}
            </span>
          ))}
        </div>
        <h3 className="text-2xl font-semibold text-slate-900">{pickLocalized(post, "title", locale)}</h3>
        <p className="text-sm leading-7 text-slate-600">{pickLocalized(post, "excerpt", locale)}</p>
        <Link
          href={`/blog/${post.slug}`}
          className="inline-flex rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-900 transition hover:border-slate-400"
        >
          {locale === "ru" ? "Читать пост" : "Read post"}
        </Link>
      </div>
    </WindowFrame>
  );
}

