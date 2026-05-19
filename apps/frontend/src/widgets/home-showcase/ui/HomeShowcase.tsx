"use client";

import { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { IconMail, IconSend } from "@tabler/icons-react";

import type { Locale, Project, SiteSettings } from "@/shared/api/types";
import { normalizeHomepageContent, normalizeProjectShowcaseMeta } from "@/shared/config/homepageContent";
import { contactSocialLinks, resolveExternalUrl, type ContactSocialKey } from "@/shared/config/socialLinks";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { cn } from "@/shared/lib/cn";
import { BrandSocialIcon } from "@/shared/ui/BrandSocialIcon";
import { ProjectScreenshotGallery } from "@/widgets/home-showcase/ui/ProjectScreenshotGallery";
import { ShowcaseVideoFrame, getProjectFallbackVariant } from "@/widgets/home-showcase/ui/ShowcaseVideoFrame";

export function HomeShowcase({
  settings,
  projects,
  locale,
  onLocaleChange,
  chatSlot,
}: {
  settings: SiteSettings;
  projects: Project[];
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
  const chatTitle = pickLocalized(content, "chat_section_title", locale);
  const chatDescription = pickLocalized(content, "chat_section_description", locale);

  return (
    <main className="min-h-screen bg-[#f7f7f5] text-[#111318]">
      <div className="mx-auto w-full max-w-[1440px] px-5 py-7 sm:px-8 lg:px-10">
        <header className="flex items-center justify-between gap-5">
          <p className="text-2xl font-bold tracking-normal sm:text-3xl">{brandName}</p>
          <div className="flex items-center gap-3">
            <LanguageControl locale={locale} onLocaleChange={onLocaleChange} />
            <a
              href={`mailto:${settings.contact_email}`}
              className="inline-flex min-h-12 items-center gap-3 rounded-lg border border-[#aeb2ba] bg-transparent px-5 text-sm font-semibold text-[#111318] transition hover:border-[#111318] hover:bg-white"
            >
              <IconSend className="h-5 w-5" aria-hidden />
              <span className="hidden sm:inline">{headerCtaLabel}</span>
            </a>
          </div>
        </header>

        <section className="grid gap-10 pb-9 pt-16 lg:grid-cols-[0.66fr_1fr] lg:items-center lg:gap-12 lg:pt-20">
          <div className="max-w-[520px]">
            <div className="mb-9 flex flex-wrap items-center gap-3 text-xs font-medium uppercase tracking-normal text-[#7a7f89]">
              {heroEyebrowItems.map((item, index) => (
                <span key={`${item}-${index}`} className="flex items-center gap-3">
                  <span>{item}</span>
                  {index < heroEyebrowItems.length - 1 ? <span className="text-[#b6bac1]">/</span> : null}
                </span>
              ))}
            </div>

            <h1 className="max-w-[520px] text-[40px] font-semibold leading-[1.28] tracking-normal text-[#111318] sm:text-5xl lg:text-[46px]">
              <RotatingHeroTitle
                title={pickLocalized(settings, "hero_title", locale)}
                items={locale === "ru" ? content.hero_title_rotating_items_ru : content.hero_title_rotating_items_en}
                intervalMs={content.hero_title_rotating_interval_ms}
                animationMs={content.hero_title_rotating_animation_ms}
                accentColor={content.hero_title_rotating_accent_color}
              />
            </h1>
            <p className="mt-9 max-w-[430px] text-lg leading-8 text-[#30343b]">
              {pickLocalized(settings, "hero_subtitle", locale)}
            </p>

            <div className="mt-12">
              <p className="mb-4 text-sm text-[#4f535c]">{technologiesLabel}</p>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-[#111318]">
                {settings.skills.map((skill, index) => (
                  <span key={`${skill}-${index}`} className="flex items-center gap-4">
                    <span>{skill}</span>
                    {index < settings.skills.length - 1 ? <span className="text-[#aeb2ba]">/</span> : null}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <ShowcaseVideoFrame
            variant={content.hero_preview.visual_variant}
            duration={content.hero_preview.video_duration}
            title={pickLocalized(settings, "hero_title", locale)}
            mediaUrl={content.hero_preview.video_url}
            coverImage={content.hero_preview.cover_image}
            className="lg:mt-2"
          />
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
    <span className="block">
      <span>{title}</span>{" "}
      <span className="inline-grid overflow-hidden align-baseline pb-1" style={{ color: accentColor }}>
        <span
          key={`${activeItem}-${activeIndex}`}
          className="animate-[hero-title-word-in_var(--hero-title-word-animation)_cubic-bezier(0.22,1,0.36,1)_both]"
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
  const showcaseMeta = normalizeProjectShowcaseMeta(project.showcase_meta, {
    visual_variant: getProjectFallbackVariant(index),
    video_duration: ["0:40", "0:35", "0:30"][index] ?? "0:40",
  });
  const screenshotItems = buildProjectScreenshots(project, locale);

  return (
    <article className="grid gap-7 lg:grid-cols-[370px_1fr] lg:gap-9">
      <div className="pt-2">
        <p className="text-4xl font-light tracking-normal text-[#a6abb3]">{String(index + 1).padStart(2, "0")}</p>
        <h2 className="mt-9 text-3xl font-semibold tracking-normal text-[#111318]">{pickLocalized(project, "title", locale)}</h2>
        <p className="mt-3 text-xl leading-7 text-[#111318]">/ {pickLocalized(project, "summary", locale)}</p>
        <p className="mt-8 max-w-[330px] text-base leading-8 text-[#4b5059]">
          {pickLocalized(project, "description", locale)}
        </p>

        <div className="mt-11">
          <p className="mb-4 text-sm text-[#4f535c]">{stackLabel}</p>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-[#111318]">
            {project.stack.map((item, stackIndex) => (
              <span key={`${project.id}-${item}`} className="flex items-center gap-4">
                <span>{item}</span>
                {stackIndex < project.stack.length - 1 ? <span className="text-[#aeb2ba]">/</span> : null}
              </span>
            ))}
          </div>
        </div>
      </div>

      {screenshotItems.length > 0 ? (
        <ProjectScreenshotGallery
          screenshots={screenshotItems}
          title={pickLocalized(project, "title", locale)}
          demoUrlToken={project.live_url}
          demoLabel={demoCtaLabel}
          className={cn(index === 0 && "bg-white")}
        />
      ) : (
        <ShowcaseVideoFrame
          variant={showcaseMeta.visual_variant}
          duration={showcaseMeta.video_duration}
          title={pickLocalized(project, "title", locale)}
          mediaUrl={project.preview_video_url}
          coverImage={project.cover_image}
          className={cn(index === 0 && "bg-white")}
        />
      )}
    </article>
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
          "border-[#aeb2ba] bg-white text-[#111318] hover:border-[#111318] hover:bg-[#111318] hover:text-white",
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

  if (mediaScreenshots.length > 0) {
    return mediaScreenshots;
  }

  return project.cover_image
    ? [
        {
          id: 0,
          url: project.cover_image,
          alt: pickLocalized(project, "title", locale),
        },
      ]
    : [];
}
