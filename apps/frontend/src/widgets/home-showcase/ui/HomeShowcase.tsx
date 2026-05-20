"use client";

/* eslint-disable @next/next/no-img-element -- Demo preview images are admin-managed media URLs. */

import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { IconMail, IconSend } from "@tabler/icons-react";

import { getKworkReviews } from "@/shared/api/client";
import type { KworkReview, KworkReviewsPage, Locale, Project, SiteSettings } from "@/shared/api/types";
import { normalizeHomepageContent, normalizeProjectShowcaseMeta } from "@/shared/config/homepageContent";
import { contactSocialLinks, resolveExternalUrl, type ContactSocialKey } from "@/shared/config/socialLinks";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { cn } from "@/shared/lib/cn";
import { BrandSocialIcon } from "@/shared/ui/BrandSocialIcon";
import { ProjectScreenshotGallery, openEncodedDemoUrl } from "@/widgets/home-showcase/ui/ProjectScreenshotGallery";
import { ShowcaseVideoFrame } from "@/widgets/home-showcase/ui/ShowcaseVideoFrame";

export function HomeShowcase({
  settings,
  projects,
  initialReviewsPage,
  locale,
  onLocaleChange,
  chatSlot,
}: {
  settings: SiteSettings;
  projects: Project[];
  initialReviewsPage: KworkReviewsPage;
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  chatSlot?: ReactNode;
}) {
  const content = normalizeHomepageContent(settings.homepage_content);
  const brandName = pickLocalized(content, "brand_name", locale) || settings.brand_name;
  const heroEyebrowItems = locale === "ru" ? content.hero_eyebrow_items_ru : content.hero_eyebrow_items_en;
  const technologiesLabel = pickLocalized(content, "technologies_label", locale);
  const projectStackLabel = pickLocalized(content, "project_stack_label", locale);
  const projectDemoCtaLabel = pickLocalized(content, "project_demo_cta_label", locale);
  const headerCtaLabel = pickLocalized(content, "header_cta_label", locale);
  const contactTitle = pickLocalized(content, "contact_title", locale);
  const contactDescription = pickLocalized(content, "contact_description", locale);
  const reviewsEyebrow = pickLocalized(content, "kwork_reviews_eyebrow", locale);
  const reviewsTitle = pickLocalized(content, "kwork_reviews_title", locale);
  const chatTitle = pickLocalized(content, "chat_section_title", locale);
  const chatDescription = pickLocalized(content, "chat_section_description", locale);
  const heroSkills = settings.skills.map((skill) => skill.trim()).filter(Boolean);
  const accentStyle = {
    "--showcase-accent-color": content.hero_title_rotating_accent_color,
  } as CSSProperties;

  return (
    <main className="min-h-screen bg-[#f7f7f5] text-[#111318]" style={accentStyle}>
      <div className="mx-auto w-full max-w-[1440px] px-5 py-7 sm:px-8 lg:px-10">
        <header className="flex items-center justify-between gap-5">
          <p className="text-2xl font-bold tracking-normal sm:text-3xl">{brandName}</p>
          <div className="flex items-center gap-3">
            <LanguageControl locale={locale} onLocaleChange={onLocaleChange} />
            <a
              href={`mailto:${settings.contact_email}`}
              className="inline-flex min-h-12 items-center gap-3 rounded-lg border border-[var(--showcase-accent-color)] bg-transparent px-5 text-sm font-semibold text-[var(--showcase-accent-color)] transition hover:bg-[var(--showcase-accent-color)] hover:text-white"
            >
              <IconSend className="h-5 w-5" aria-hidden />
              <span className="hidden sm:inline">{headerCtaLabel}</span>
            </a>
          </div>
        </header>

        <section
          className="grid gap-10 pb-9 pt-16 lg:grid-cols-1 lg:items-center lg:gap-12 lg:pt-20"
        >
          <div className="max-w-[980px]">
            <div className="mb-9 flex flex-wrap items-center gap-3 text-xs font-medium uppercase tracking-normal text-[#7a7f89]">
              {heroEyebrowItems.map((item, index) => (
                <span key={`${item}-${index}`} className="flex items-center gap-3">
                  <span>{item}</span>
                  {index < heroEyebrowItems.length - 1 ? <span className="text-[#b6bac1]">/</span> : null}
                </span>
              ))}
            </div>

            <h1
              className="max-w-[980px] text-[40px] font-semibold leading-[1.28] tracking-normal text-[#111318] sm:text-5xl lg:text-[46px]"
            >
              <RotatingHeroTitle
                title={pickLocalized(settings, "hero_title", locale)}
                items={locale === "ru" ? content.hero_title_rotating_items_ru : content.hero_title_rotating_items_en}
                intervalMs={content.hero_title_rotating_interval_ms}
                animationMs={content.hero_title_rotating_animation_ms}
                accentColor={content.hero_title_rotating_accent_color}
              />
            </h1>
            <p className="mt-9 max-w-[720px] text-lg leading-8 text-[#30343b]">
              {pickLocalized(settings, "hero_subtitle", locale)}
            </p>

            {heroSkills.length > 0 ? (
              <div className="mt-12 max-w-[980px]">
                <p className="mb-4 text-sm text-[#4f535c]">{technologiesLabel}</p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-[#111318] xl:flex-nowrap">
                  {heroSkills.map((skill, index) => (
                    <span key={`${skill}-${index}`} className="flex min-w-0 shrink-0 items-center gap-4">
                      <span className="whitespace-nowrap">{skill}</span>
                      {index < heroSkills.length - 1 ? <span className="text-[#aeb2ba]">/</span> : null}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </section>

        {projects.length > 0 ? (
          <section className="space-y-7 py-6 lg:space-y-8">
            {projects.map((project, index) => (
              <ProjectShowcaseRow
                key={project.id}
                project={project}
                index={index}
                locale={locale}
                stackLabel={projectStackLabel}
                demoCtaLabel={projectDemoCtaLabel}
              />
            ))}
          </section>
        ) : null}

        <KworkReviewsSection
          initialPage={initialReviewsPage}
          eyebrow={reviewsEyebrow}
          title={reviewsTitle}
          locale={locale}
        />

        <ContactCta
          settings={settings}
        title={contactTitle}
        description={contactDescription}
      />

        {settings.chat_bot_enabled && chatSlot ? (
          <section className="grid gap-8 py-12 lg:grid-cols-[0.38fr_1fr] lg:items-start">
            <div className="max-w-[360px]">
              <p className="text-sm uppercase tracking-normal text-[#8c929c]">AI</p>
              <h2 className="mt-4 text-3xl font-semibold leading-tight tracking-normal">{chatTitle}</h2>
              <p className="mt-5 whitespace-pre-line text-base leading-7 text-[#4b5059]">{chatDescription}</p>
            </div>
            <div>{chatSlot}</div>
          </section>
        ) : null}
      </div>
    </main>
  );
}

const KWORK_PROFILE_URL = "https://kwork.ru/user/portfolio-dev";
const REVIEWS_BATCH_SIZE = 3;

function KworkReviewsSection({
  initialPage,
  eyebrow,
  title,
  locale,
}: {
  initialPage: KworkReviewsPage;
  eyebrow: string;
  title: string;
  locale: Locale;
}) {
  const [reviews, setReviews] = useState<KworkReview[]>(initialPage.items);
  const [total, setTotal] = useState(initialPage.total);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const hasMoreReviews = reviews.length < total;
  const reviewsCountLabel = locale === "ru" ? "отзывов" : "reviews";
  const loadingMoreLabel = locale === "ru" ? "Загружаю..." : "Loading...";
  const loadMoreLabel = locale === "ru" ? "Показать еще" : "Show more";

  useEffect(() => {
    setReviews(initialPage.items);
    setTotal(initialPage.total);
    setLoadError(null);
  }, [initialPage.items, initialPage.total]);

  async function handleLoadMore() {
    if (isLoadingMore || !hasMoreReviews) {
      return;
    }
    setIsLoadingMore(true);
    try {
      const nextPage = await getKworkReviews({
        offset: reviews.length,
        limit: REVIEWS_BATCH_SIZE,
      });
      setReviews((current) => [...current, ...nextPage.items]);
      setTotal(nextPage.total);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Не удалось загрузить отзывы");
    } finally {
      setIsLoadingMore(false);
    }
  }

  if (reviews.length === 0) {
    return null;
  }

  return (
    <section className="py-12">
      <div className="mb-7 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-normal text-[#8c929c]">{eyebrow}</p>
          <h2 className="mt-4 max-w-[720px] text-3xl font-semibold leading-tight tracking-normal text-[#111318] sm:text-4xl">
            <KworkLinkedTitle title={title} />
          </h2>
        </div>
        <p className="text-sm text-[#6b7079]">
          {total} {reviewsCountLabel}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {reviews.map((review) => (
          <KworkReviewCard key={review.id} review={review} />
        ))}
      </div>

      {loadError ? (
        <p className="mt-4 text-center text-sm text-rose-600">{loadError}</p>
      ) : null}

      {hasMoreReviews ? (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={() => void handleLoadMore()}
            disabled={isLoadingMore}
            className="inline-flex min-h-11 items-center justify-center rounded-lg border border-[#111318] bg-[#111318] px-5 text-sm font-semibold text-white transition hover:bg-white hover:text-[#111318]"
          >
            {isLoadingMore ? loadingMoreLabel : loadMoreLabel}
          </button>
        </div>
      ) : null}
    </section>
  );
}

function KworkLinkedTitle({ title }: { title: string }) {
  const marker = "kwork.ru";
  const index = title.toLowerCase().indexOf(marker);

  if (index < 0) {
    return <>{title}</>;
  }

  return (
    <>
      {title.slice(0, index)}
      <a
        href={KWORK_PROFILE_URL}
        target="_blank"
        rel="noreferrer"
        className="underline decoration-[#111318]/25 underline-offset-4 transition hover:decoration-[#111318]"
      >
        {title.slice(index, index + marker.length)}
      </a>
      {title.slice(index + marker.length)}
    </>
  );
}

function KworkReviewCard({ review }: { review: KworkReview }) {
  return (
    <article className="flex min-h-[250px] flex-col rounded-lg border border-[#dfe2e7] bg-white/70 p-5 shadow-[0_18px_55px_rgba(17,19,24,0.06)]">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-[#111318] text-sm font-semibold uppercase text-white">
            {getAuthorInitials(review.author_name)}
          </div>
          <div className="min-w-0">
            {review.author_url ? (
              <a
                href={review.author_url}
                target="_blank"
                rel="noreferrer"
                className="block truncate text-base font-semibold text-[#111318] underline decoration-transparent underline-offset-4 transition hover:decoration-[#111318]/30"
              >
                {review.author_name}
              </a>
            ) : (
              <p className="truncate text-base font-semibold text-[#111318]">{review.author_name}</p>
            )}
            <p className="mt-1 text-xs uppercase tracking-normal text-[#8c929c]">
              {review.time_ago || review.reviewed_at?.slice(0, 10) || "Kwork"}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-0.5 text-sm text-[#111318]" aria-label={`${review.rating} of 5`}>
          {Array.from({ length: 5 }).map((_, index) => (
            <span key={index} className={index < review.rating ? "opacity-100" : "opacity-20"}>
              ★
            </span>
          ))}
        </div>
      </div>

      <p className="mt-5 line-clamp-6 flex-1 text-base leading-7 text-[#30343b]">{review.text}</p>

      {review.project_title ? (
        <p className="mt-5 border-t border-[#e6e8ed] pt-4 text-sm leading-6 text-[#6b7079]">
          {review.project_title}
        </p>
      ) : null}
    </article>
  );
}

function getAuthorInitials(name: string) {
  const parts = name
    .trim()
    .split(/\s|_/)
    .map((part) => part.trim())
    .filter(Boolean);
  const initials = parts.slice(0, 2).map((part) => part[0]).join("");
  return initials || "KW";
}

function RotatingHeroTitle({
  title,
  items,
  intervalMs,
  animationMs,
  accentColor,
}: {
  title: string;
  items: string[];
  intervalMs: number;
  animationMs: number;
  accentColor: string;
}) {
  const rotatingItems = useMemo(() => items.map((item) => item.trim()).filter(Boolean), [items]);
  const rotatingItemsKey = useMemo(() => rotatingItems.join("\n"), [rotatingItems]);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setActiveIndex(0);
  }, [rotatingItemsKey]);

  useEffect(() => {
    if (rotatingItems.length < 2) {
      return;
    }

    const timer = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % rotatingItems.length);
    }, Math.max(600, intervalMs));

    return () => window.clearInterval(timer);
  }, [intervalMs, rotatingItems.length]);

  const activeItem = rotatingItems[activeIndex] ?? rotatingItems[0];

  if (!activeItem) {
    return <>{title}</>;
  }

  return (
    <span className="block sm:inline">
      <span className="block sm:inline">{title}</span>
      <span
        className="mt-1 block min-h-[2.56em] overflow-hidden pb-1 sm:ml-2 sm:mt-0 sm:inline-grid sm:min-h-0 sm:align-baseline"
        style={{ color: accentColor }}
      >
        <span
          key={`${activeItem}-${activeIndex}`}
          className="block animate-[hero-title-word-in_var(--hero-title-word-animation)_cubic-bezier(0.22,1,0.36,1)_both]"
          style={{ "--hero-title-word-animation": `${Math.max(200, animationMs)}ms` } as CSSProperties}
        >
          {activeItem}
        </span>
      </span>
    </span>
  );
}

function LanguageControl({
  locale,
  onLocaleChange,
}: {
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
}) {
  return (
    <div className="inline-grid h-12 w-24 shrink-0 grid-cols-2 overflow-hidden rounded-lg border border-[#d0d3d8] bg-white/50">
      {(["ru", "en"] as Locale[]).map((item) => {
        const isActive = item === locale;

        return (
          <button
            key={item}
            type="button"
            onClick={() => onLocaleChange(item)}
            className={cn(
              "grid h-full min-w-0 place-items-center px-0 text-center text-xs font-semibold uppercase leading-none tracking-normal transition",
              isActive ? "bg-[#111318] text-white" : "text-[#5f646d] hover:bg-white hover:text-[#111318]",
            )}
          >
            {item}
          </button>
        );
      })}
    </div>
  );
}

function ProjectShowcaseRow({
  project,
  index,
  locale,
  stackLabel,
  demoCtaLabel,
}: {
  project: Project;
  index: number;
  locale: Locale;
  stackLabel: string;
  demoCtaLabel: string;
}) {
  const projectTitle = pickLocalized(project, "title", locale);
  const projectSummary = pickLocalized(project, "summary", locale).trim();
  const showcaseMeta = normalizeProjectShowcaseMeta(project.showcase_meta);
  const screenshotItems = buildProjectScreenshots(project, locale);
  const projectStack = project.stack.map((item) => item.trim()).filter(Boolean);
  const mediaClassName = "lg:self-center";
  const projectMedia =
    showcaseMeta.media_mode === "video" && (project.preview_video_url || project.cover_image) ? (
      <ShowcaseVideoFrame
        variant="uploaded-media"
        duration={showcaseMeta.video_duration}
        title={projectTitle}
        mediaUrl={project.preview_video_url}
        coverImage={project.cover_image}
        className={mediaClassName}
      />
    ) : showcaseMeta.media_mode === "demo" && project.live_url ? (
      <ProjectDemoPreview
        coverImage={project.cover_image}
        title={projectTitle}
        demoUrlToken={project.live_url}
        label={demoCtaLabel}
        className={mediaClassName}
      />
    ) : showcaseMeta.media_mode === "screenshots" && screenshotItems.length > 0 ? (
      <ProjectScreenshotGallery screenshots={screenshotItems} title={projectTitle} className={mediaClassName} />
    ) : null;

  return (
    <article className="space-y-6 lg:space-y-7">
      <header className="grid gap-4 lg:grid-cols-[86px_minmax(0,1fr)] lg:items-end">
        <p className="text-4xl font-light tracking-normal text-[#a6abb3]">{String(index + 1).padStart(2, "0")}</p>
        <div className="min-w-0">
          <h2 className="flex items-baseline gap-3 overflow-x-auto pb-1 text-3xl font-semibold tracking-normal text-[#111318] lg:whitespace-nowrap">
            <span className="shrink-0">{projectTitle}</span>
            {projectSummary ? (
              <span className="shrink-0 text-xl font-normal leading-7 text-[#111318]">/ {projectSummary}</span>
            ) : null}
          </h2>
        </div>
      </header>

      <div
        className={cn(
          "grid gap-7 lg:gap-9",
          projectMedia ? "lg:grid-cols-[370px_1fr] lg:items-center" : "lg:grid-cols-1",
        )}
      >
        <div>
          <p
            className={cn(
              "whitespace-pre-line text-base leading-8 text-[#4b5059]",
              projectMedia ? "max-w-[330px]" : "max-w-[680px]",
            )}
          >
            {pickLocalized(project, "description", locale)}
          </p>
        </div>

        {projectMedia}
      </div>

      {projectStack.length > 0 ? (
        <footer>
          <p className="mb-4 text-sm text-[#4f535c]">{stackLabel}</p>
          <div className="flex items-center gap-x-4 overflow-x-auto pb-1 text-sm text-[#111318]">
            {projectStack.map((item, stackIndex) => (
              <span key={`${project.id}-${item}`} className="flex shrink-0 items-center gap-4">
                <span className="whitespace-nowrap">{item}</span>
                {stackIndex < projectStack.length - 1 ? <span className="text-[#aeb2ba]">/</span> : null}
              </span>
            ))}
          </div>
        </footer>
      ) : null}
    </article>
  );
}

function ProjectDemoPreview({
  coverImage,
  title,
  demoUrlToken,
  label,
  className,
}: {
  coverImage?: string | null;
  title: string;
  demoUrlToken: string;
  label: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative isolate overflow-hidden rounded-lg border border-black/10 bg-[#0d0f14] shadow-[0_24px_70px_rgba(15,23,42,0.16)]",
        className,
      )}
    >
      <div className="relative grid aspect-[16/9] min-h-[250px] w-full place-items-center overflow-hidden bg-[#0d0f14]">
        {coverImage ? (
          <img
            src={coverImage}
            alt=""
            className="absolute inset-0 h-full w-full object-contain object-center"
            aria-hidden
          />
        ) : (
          <div className="grid h-full place-items-center bg-[linear-gradient(135deg,#111318,#252b36)] px-8 text-center text-sm font-medium text-white/70">
            {title}
          </div>
        )}
      </div>
      <span className="pointer-events-none absolute inset-0 z-10 bg-black/56" />
      <button
        type="button"
        onClick={() => openEncodedDemoUrl(demoUrlToken)}
        className="absolute left-1/2 top-1/2 z-20 max-w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-white/15 bg-black/80 px-5 py-3 text-sm font-semibold text-white shadow-[0_18px_50px_rgba(0,0,0,0.42)] ring-1 ring-white/10 transition hover:bg-black sm:px-6"
      >
        {label}
      </button>
    </div>
  );
}

function ContactCta({
  settings,
  title,
  description,
}: {
  settings: SiteSettings;
  title: string;
  description: string;
}) {
  return (
    <section className="grid gap-8 py-11 lg:grid-cols-[0.3fr_1px_0.35fr_0.35fr] lg:items-center">
      <h2 className="whitespace-pre-line text-4xl font-semibold leading-tight tracking-normal text-[#111318]">
        {title}
      </h2>
      <div className="hidden h-20 w-px bg-[#c8ccd3] lg:block" />
      <p className="max-w-[360px] whitespace-pre-line text-base leading-7 text-[#4b5059]">{description}</p>
      <ContactLinksGroup socials={settings.socials} email={settings.contact_email} />
    </section>
  );
}

function ContactLinksGroup({ socials, email }: { socials: SiteSettings["socials"]; email: string }) {
  return (
    <div className="inline-grid min-h-10 grid-cols-6 gap-2 justify-self-start lg:min-h-9 lg:justify-self-end">
      {contactSocialLinks.map((item) => {
        const href = resolveExternalUrl(socials[item.key]);

        if (!href) {
          return (
            <span
              key={item.key}
              title={`${item.label} is not configured`}
              className={cn(contactIconClassName, "border-[#d7dbe2] bg-white/40 text-[#a1a7b1]")}
            >
              <SocialMark socialKey={item.key} />
            </span>
          );
        }

        return (
          <a
            key={item.key}
            href={href}
            target="_blank"
            rel="noreferrer"
            aria-label={item.label}
            title={item.label}
            className={cn(
              contactIconClassName,
              "group border-[#111318] bg-[#111318] text-white hover:bg-white hover:text-[#111318]",
            )}
          >
            <SocialMark socialKey={item.key} />
          </a>
        );
      })}
      <a
        href={`mailto:${email}`}
        aria-label="Email"
        title="Email"
        className={cn(
          contactIconClassName,
          "border-[var(--showcase-accent-color)] bg-white text-[var(--showcase-accent-color)] hover:bg-[var(--showcase-accent-color)] hover:text-white",
        )}
      >
        <IconMail className="h-5 w-5 lg:h-4 lg:w-4" aria-hidden />
      </a>
    </div>
  );
}

const contactIconClassName =
  "grid h-10 w-10 min-w-0 place-items-center rounded-lg border text-sm font-semibold uppercase leading-none tracking-normal transition lg:h-9 lg:w-9";

function SocialMark({ socialKey }: { socialKey: ContactSocialKey }) {
  return <BrandSocialIcon socialKey={socialKey} className="h-5 w-5 lg:h-4 lg:w-4" />;
}

function buildProjectScreenshots(project: Project, locale: Locale) {
  const mediaScreenshots = project.media_items
    .filter((item) => item.asset_type === "image")
    .sort((first, second) => first.sort_order - second.sort_order)
    .map((item) => ({
      id: item.id,
      url: item.url,
      alt: pickLocalized(item, "alt", locale) || pickLocalized(project, "title", locale),
    }));

  return mediaScreenshots;
}
