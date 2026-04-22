import Link from "next/link";

import type { BlogPost, Locale } from "@/shared/api/types";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { PillBadge } from "@/shared/ui/PillBadge";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function BlogCard({ post, locale }: { post: BlogPost; locale: Locale }) {
  return (
    <WindowFrame
      title={post.post_type.toUpperCase()}
      subtitle={post.category ? pickLocalized(post.category, "name", locale) : undefined}
      variant="tinted"
      decorativeTone={post.post_type === "video" ? "rose" : "sand"}
      bodyClassName="h-full"
    >
      <div className="flex h-full flex-col gap-5">
        {post.cover_image ? (
          <div
            className="h-56 rounded-[28px] border border-white/80 bg-cover bg-center shadow-[var(--shadow-soft-sm)]"
            style={{ backgroundImage: `url(${post.cover_image})` }}
          />
        ) : null}
        <div className="flex flex-1 flex-col gap-4">
          <div className="flex flex-wrap gap-2">
            {post.tags.map((tag) => (
              <PillBadge key={tag} tone="accent" size="sm" className="normal-case tracking-normal">
                #{tag}
              </PillBadge>
            ))}
          </div>
          <h3 className="text-2xl font-semibold leading-tight tracking-[-0.03em] text-[var(--text-primary)]">
            {pickLocalized(post, "title", locale)}
          </h3>
          <p className="text-sm leading-7 text-[var(--text-secondary)]">{pickLocalized(post, "excerpt", locale)}</p>
        </div>
        <Link
          href={`/blog/${post.slug}`}
          className="inline-flex w-fit rounded-[var(--radius-pill)] border border-[var(--border-soft)] bg-white/75 px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] transition hover:border-[var(--border-strong)] hover:bg-white"
        >
          {locale === "ru" ? "Читать пост" : "Read post"}
        </Link>
      </div>
    </WindowFrame>
  );
}
