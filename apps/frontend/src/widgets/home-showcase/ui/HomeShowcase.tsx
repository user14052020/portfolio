"use client";

/* eslint-disable @next/next/no-img-element -- Demo preview images are admin-managed media URLs. */

import { useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { IconChevronDown, IconChevronLeft, IconChevronRight, IconChevronUp, IconMail, IconSend } from "@tabler/icons-react";

import { getKworkReviews } from "@/shared/api/client";
import type { KworkReview, KworkReviewsPage, Locale, Project, SiteSettings } from "@/shared/api/types";
import {
  normalizeHomepageContent,
  normalizeProjectShowcaseMeta,
  projectTypeSections,
  type ProjectType,
} from "@/shared/config/homepageContent";
import { contactSocialLinks, resolveExternalUrl, type ContactSocialKey } from "@/shared/config/socialLinks";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { cn } from "@/shared/lib/cn";
import { BrandSocialIcon } from "@/shared/ui/BrandSocialIcon";
import { ProjectScreenshotGallery, openEncodedDemoUrl } from "@/widgets/home-showcase/ui/ProjectScreenshotGallery";
import { MobileVideoFrame, ShowcaseVideoFrame } from "@/widgets/home-showcase/ui/ShowcaseVideoFrame";

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
  const projectGroups = useMemo(
    () =>
      projectTypeSections
        .map((section) => ({
          ...section,
          projects: projects.filter(
            (project) => normalizeProjectShowcaseMeta(project.showcase_meta).project_type === section.value,
          ),
        }))
        .filter((group) => group.projects.length > 0),
    [projects],
  );
  const accentStyle = {
    "--showcase-accent-color": content.hero_title_rotating_accent_color,
  } as CSSProperties;

  return (
    <main className="min-h-screen bg-white text-[#111318]" style={accentStyle}>
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

        {projectGroups.length > 0 ? (
          <section className="py-6">
            {projectGroups.map((group) => (
              <ProjectTypeSlider
                key={group.value}
                group={group}
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
const PROJECT_SLIDER_SECONDS = 60;
const PROJECT_DESCRIPTION_COLLAPSED_LINES = 6;
const PROJECT_DESCRIPTION_MOBILE_COLLAPSED_LINES = 2;
const PROJECT_DESCRIPTION_DESKTOP_QUERY = "(min-width: 640px)";

type ProjectSectionThemeStyle = CSSProperties & Record<`--project-${string}`, string>;

const projectSectionThemeStyles: Record<ProjectType, ProjectSectionThemeStyle> = {
  web: {
    "--project-bg": "#eef5ff",
    "--project-border": "#c7d8f1",
    "--project-title": "#0e1a2b",
    "--project-text": "#405169",
    "--project-muted": "#5d6f88",
    "--project-divider": "#94a9c6",
    "--project-control-bg": "rgba(255,255,255,0.82)",
    "--project-control-border": "#b8cbe5",
    "--project-control-fill": "#0e1a2b",
    "--project-control-muted": "#c4d2e8",
    "--project-control-contrast": "#ffffff",
    "--project-control-inner-bg": "#ffffff",
    "--project-fade-from": "rgba(238,245,255,0.15)",
  },
  one_c: {
    "--project-bg": "#202318",
    "--project-border": "#51472a",
    "--project-title": "#fff5d6",
    "--project-text": "#e7dec2",
    "--project-muted": "#c8ba88",
    "--project-divider": "#d6ae43",
    "--project-control-bg": "rgba(255,255,255,0.1)",
    "--project-control-border": "#786735",
    "--project-control-fill": "#f1c64b",
    "--project-control-muted": "#5d5436",
    "--project-control-contrast": "#17150f",
    "--project-control-inner-bg": "#292b1f",
    "--project-fade-from": "rgba(32,35,24,0.15)",
  },
  mobile_app: {
    "--project-bg": "#edf8f5",
    "--project-border": "#bddbd3",
    "--project-title": "#102621",
    "--project-text": "#405e56",
    "--project-muted": "#55766d",
    "--project-divider": "#88b5aa",
    "--project-control-bg": "rgba(255,255,255,0.8)",
    "--project-control-border": "#a8cdc3",
    "--project-control-fill": "#102621",
    "--project-control-muted": "#bdd9d1",
    "--project-control-contrast": "#ffffff",
    "--project-control-inner-bg": "#ffffff",
    "--project-fade-from": "rgba(237,248,245,0.15)",
  },
  animation: {
    "--project-bg": "#181421",
    "--project-border": "#42354f",
    "--project-title": "#faf4ff",
    "--project-text": "#d8cde5",
    "--project-muted": "#bbaacf",
    "--project-divider": "#8f72b6",
    "--project-control-bg": "rgba(255,255,255,0.1)",
    "--project-control-border": "#5b4770",
    "--project-control-fill": "#d6b8ff",
    "--project-control-muted": "#4c405c",
    "--project-control-contrast": "#17111f",
    "--project-control-inner-bg": "#241c30",
    "--project-fade-from": "rgba(24,20,33,0.15)",
  },
};

type ProjectTypeGroup = (typeof projectTypeSections)[number] & {
  projects: Project[];
};

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

function ProjectTypeSlider({
  group,
  locale,
  stackLabel,
  demoCtaLabel,
}: {
  group: ProjectTypeGroup;
  locale: Locale;
  stackLabel: string;
  demoCtaLabel: string;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [remainingSeconds, setRemainingSeconds] = useState(PROJECT_SLIDER_SECONDS);
  const [isMediaPlaying, setIsMediaPlaying] = useState(false);
  const projectIdsKey = useMemo(() => group.projects.map((project) => project.id).join(","), [group.projects]);
  const activeProject = group.projects[Math.min(activeIndex, group.projects.length - 1)];
  const groupTitle = pickLocalized(group, "title", locale);
  const themeStyle = projectSectionThemeStyles[group.value];

  useEffect(() => {
    setActiveIndex(0);
  }, [projectIdsKey]);

  useEffect(() => {
    setRemainingSeconds(PROJECT_SLIDER_SECONDS);
    setIsMediaPlaying(false);
  }, [activeIndex, projectIdsKey]);

  useEffect(() => {
    if (group.projects.length < 2 || isMediaPlaying) {
      return;
    }

    const countdownTimer = window.setInterval(() => {
      setRemainingSeconds((current) => {
        if (current <= 1) {
          setActiveIndex((index) => (index + 1) % group.projects.length);
          return PROJECT_SLIDER_SECONDS;
        }

        return current - 1;
      });
    }, 1000);

    return () => window.clearInterval(countdownTimer);
  }, [group.projects.length, isMediaPlaying, projectIdsKey]);

  if (!activeProject) {
    return null;
  }

  function showPreviousProject() {
    setActiveIndex((current) => (current - 1 + group.projects.length) % group.projects.length);
  }

  function showNextProject() {
    setActiveIndex((current) => (current + 1) % group.projects.length);
  }

  return (
    <section
      className="relative left-1/2 w-screen -translate-x-1/2 border-y border-[color:var(--project-border)] bg-[var(--project-bg)] text-[color:var(--project-title)]"
      style={themeStyle}
    >
      <div className="mx-auto w-full max-w-[1440px] px-5 py-8 sm:px-8 lg:px-10">
      <div className="hidden">
        <div>
          <p className="text-sm uppercase tracking-normal text-[#8c929c]">Portfolio</p>
          <h2 className="mt-3 text-3xl font-semibold leading-tight tracking-normal text-[#111318] sm:text-4xl">
            {groupTitle}
          </h2>
        </div>
        <p className="text-sm text-[#6b7079]">
          {group.projects.length} {locale === "ru" ? "проектов" : "projects"}
        </p>
      </div>

      <ProjectShowcaseRow
        project={activeProject}
        index={activeIndex}
        locale={locale}
        stackLabel={stackLabel}
        demoCtaLabel={demoCtaLabel}
        onMediaPlaybackChange={setIsMediaPlaying}
      />

      {group.projects.length > 1 ? (
        <ProjectSliderControls
          activeIndex={activeIndex}
          total={group.projects.length}
          remainingSeconds={remainingSeconds}
          onPrevious={showPreviousProject}
          onNext={showNextProject}
          onSelect={setActiveIndex}
        />
      ) : null}
      </div>
    </section>
  );
}

function ProjectSliderControls({
  activeIndex,
  total,
  remainingSeconds,
  onPrevious,
  onNext,
  onSelect,
}: {
  activeIndex: number;
  total: number;
  remainingSeconds: number;
  onPrevious: () => void;
  onNext: () => void;
  onSelect: (index: number) => void;
}) {
  const countdownProgress = 1 - remainingSeconds / PROJECT_SLIDER_SECONDS;

  return (
    <div className="mt-5 flex justify-end">
      <div className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--project-control-border)] bg-[var(--project-control-bg)] p-2 shadow-[0_16px_46px_rgba(17,19,24,0.08)] backdrop-blur">
        <div className="hidden items-center gap-1 sm:flex">
          {Array.from({ length: total }).map((_, index) => (
            <button
              key={index}
              type="button"
              aria-label={`Show project ${index + 1}`}
              onClick={() => onSelect(index)}
              className={cn(
                "h-2.5 rounded-full transition",
                index === activeIndex
                  ? "w-6 bg-[var(--project-control-fill)]"
                  : "w-2.5 bg-[var(--project-control-muted)] hover:bg-[var(--project-divider)]",
              )}
            />
          ))}
        </div>

        <div
          className="mx-1 grid h-12 w-12 shrink-0 place-items-center rounded-full transition-[background] duration-300"
          style={{
            background: `conic-gradient(var(--project-control-fill) ${Math.max(0, Math.min(countdownProgress, 1)) * 360}deg, var(--project-control-muted) 0deg)`,
          }}
          aria-label={`${remainingSeconds} seconds to next project`}
        >
          <span className="grid h-9 w-9 place-items-center rounded-full bg-[var(--project-control-inner-bg)] text-xs font-semibold tabular-nums text-[color:var(--project-control-fill)]">
            {remainingSeconds}
          </span>
        </div>

        <span className="hidden min-w-[54px] text-xs font-semibold tabular-nums text-[color:var(--project-title)] sm:inline">
          {String(activeIndex + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
        </span>

        <button
          type="button"
          aria-label="Previous project"
          onClick={onPrevious}
          className="grid h-9 w-9 place-items-center rounded-md border border-[color:var(--project-control-border)] bg-[var(--project-control-inner-bg)] text-[color:var(--project-control-fill)] transition hover:border-[color:var(--project-control-fill)] hover:bg-[var(--project-control-fill)] hover:text-[color:var(--project-control-contrast)]"
        >
          <IconChevronLeft className="h-5 w-5" aria-hidden />
        </button>
        <button
          type="button"
          aria-label="Next project"
          onClick={onNext}
          className="grid h-9 w-9 place-items-center rounded-md border border-[color:var(--project-control-fill)] bg-[var(--project-control-fill)] text-[color:var(--project-control-contrast)] transition hover:bg-[var(--project-control-inner-bg)] hover:text-[color:var(--project-control-fill)]"
        >
          <IconChevronRight className="h-5 w-5" aria-hidden />
        </button>
      </div>
    </div>
  );
}

function ProjectShowcaseRow({
  project,
  index,
  locale,
  stackLabel,
  demoCtaLabel,
  onMediaPlaybackChange,
}: {
  project: Project;
  index: number;
  locale: Locale;
  stackLabel: string;
  demoCtaLabel: string;
  onMediaPlaybackChange?: (isPlaying: boolean) => void;
}) {
  const projectTitle = pickLocalized(project, "title", locale);
  const projectSummary = pickLocalized(project, "summary", locale).trim();
  const projectDescription = pickLocalized(project, "description", locale).trim();
  const showcaseMeta = normalizeProjectShowcaseMeta(project.showcase_meta);
  const screenshotItems = buildProjectScreenshots(project, locale);
  const projectStack = project.stack.map((item) => item.trim()).filter(Boolean);
  const mediaClassName = "lg:self-center";
  const projectMedia =
    showcaseMeta.media_mode === "mobile_video" && (project.preview_video_url || project.cover_image) ? (
      <MobileVideoFrame
        duration={showcaseMeta.video_duration}
        title={projectTitle}
        mediaUrl={project.preview_video_url}
        coverImage={project.cover_image}
        className={mediaClassName}
        onPlaybackStateChange={onMediaPlaybackChange}
      />
    ) : showcaseMeta.media_mode === "video" && (project.preview_video_url || project.cover_image) ? (
      <ShowcaseVideoFrame
        variant="uploaded-media"
        duration={showcaseMeta.video_duration}
        title={projectTitle}
        mediaUrl={project.preview_video_url}
        coverImage={project.cover_image}
        className={mediaClassName}
        onPlaybackStateChange={onMediaPlaybackChange}
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
      <header>
        <div className="min-w-0">
          <h2 className="flex items-center gap-3 overflow-x-auto pb-1 text-3xl font-semibold leading-tight tracking-normal text-[color:var(--project-title)] lg:whitespace-nowrap">
            <span className="shrink-0 leading-tight">{projectTitle}</span>
            {projectSummary ? (
              <span className="shrink-0 text-xl font-normal leading-tight text-[color:var(--project-title)] opacity-[0.82]">/ {projectSummary}</span>
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
        <ProjectDescription
          projectId={project.id}
          text={projectDescription}
          locale={locale}
          className={projectMedia ? "max-w-[330px]" : "max-w-[680px]"}
        />

        {projectMedia}
      </div>

      {projectStack.length > 0 ? (
        <footer>
          <div className="flex items-center gap-x-4 overflow-x-auto pb-1 text-sm text-[color:var(--project-title)]">
            {projectStack.map((item, stackIndex) => (
              <span key={`${project.id}-${item}`} className="flex shrink-0 items-center gap-4">
                <span className="whitespace-nowrap">{item}</span>
                {stackIndex < projectStack.length - 1 ? <span className="text-[color:var(--project-divider)]">/</span> : null}
              </span>
            ))}
          </div>
        </footer>
      ) : null}
    </article>
  );
}

function ProjectDescription({
  projectId,
  text,
  locale,
  className,
}: {
  projectId: number;
  text: string;
  locale: Locale;
  className?: string;
}) {
  const contentRef = useRef<HTMLParagraphElement | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [canExpand, setCanExpand] = useState(false);
  const expandAriaLabel = locale === "ru" ? "Показать описание полностью" : "Show full description";
  const collapseAriaLabel = locale === "ru" ? "Скрыть описание" : "Hide description";

  useEffect(() => {
    setIsExpanded(false);
  }, [projectId, text]);

  useEffect(() => {
    const contentElement = contentRef.current;

    if (!contentElement) {
      setCanExpand(false);
      return;
    }

    const measuredElement = contentElement;
    const mediaQuery =
      typeof window.matchMedia === "function" ? window.matchMedia(PROJECT_DESCRIPTION_DESKTOP_QUERY) : null;

    function syncOverflowState() {
      const lineHeight = Number.parseFloat(window.getComputedStyle(measuredElement).lineHeight);
      const safeLineHeight = Number.isFinite(lineHeight) ? lineHeight : 32;
      const collapsedLines = mediaQuery?.matches
        ? PROJECT_DESCRIPTION_COLLAPSED_LINES
        : PROJECT_DESCRIPTION_MOBILE_COLLAPSED_LINES;
      const collapsedHeight = collapsedLines * safeLineHeight;

      setCanExpand(measuredElement.scrollHeight > collapsedHeight + 1);
    }

    syncOverflowState();

    const resizeObserver =
      typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => syncOverflowState());
    resizeObserver?.observe(measuredElement);
    window.addEventListener("resize", syncOverflowState);
    mediaQuery?.addEventListener("change", syncOverflowState);

    return () => {
      resizeObserver?.disconnect();
      window.removeEventListener("resize", syncOverflowState);
      mediaQuery?.removeEventListener("change", syncOverflowState);
    };
  }, [text]);

  return (
    <div className={cn(className)}>
      <div className={cn("relative", isExpanded ? "min-h-16 sm:min-h-48" : "h-[5.5rem] overflow-hidden sm:h-[13.5rem]")}>
        <p ref={contentRef} className="whitespace-pre-line text-base leading-8 text-[color:var(--project-text)]">
          {text}
        </p>
        {!isExpanded && canExpand ? (
          <span
            className="pointer-events-none absolute inset-x-0 bottom-0 top-[4.75rem] sm:top-[12.75rem]"
            style={{ background: "linear-gradient(to bottom, var(--project-fade-from), var(--project-bg))" }}
            aria-hidden
          />
        ) : null}
      </div>
      <div className="mt-2 min-h-8">
        {canExpand ? (
          <button
            type="button"
            aria-label={isExpanded ? collapseAriaLabel : expandAriaLabel}
            onClick={() => setIsExpanded((current) => !current)}
            className="grid h-8 w-full place-items-center rounded-md text-[color:var(--project-control-fill)] transition hover:text-[color:var(--project-title)]"
          >
            {isExpanded ? <IconChevronUp className="h-5 w-5" aria-hidden /> : <IconChevronDown className="h-5 w-5" aria-hidden />}
          </button>
        ) : null}
      </div>
    </div>
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
