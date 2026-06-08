import type { Metadata, Viewport } from "next";
import { ColorSchemeScript } from "@mantine/core";
import { cookies } from "next/headers";
import localFont from "next/font/local";

import type { Locale } from "@/shared/api/types";
import { AppProviders } from "@/providers/AppProviders";
import { getSiteSettings } from "@/shared/api/client";
import { env } from "@/shared/config/env";
import { normalizeHomepageContent } from "@/shared/config/homepageContent";
import { pickLocalized } from "@/shared/i18n/dictionaries";
import { fallbackSettings } from "@/shared/mock/content";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@/app/globals.css";

const aaStetica = localFont({
  src: [
    {
      path: "./fonts/AA Stetica Light.otf",
      weight: "300",
      style: "normal"
    },
    {
      path: "./fonts/AA Stetica Light Italic.otf",
      weight: "300",
      style: "italic"
    },
    {
      path: "./fonts/AA Stetica Regular.otf",
      weight: "400",
      style: "normal"
    },
    {
      path: "./fonts/AA Stetica Italic.otf",
      weight: "400",
      style: "italic"
    },
    {
      path: "./fonts/AA Stetica Medium.otf",
      weight: "500",
      style: "normal"
    },
    {
      path: "./fonts/AA Stetica Medium Italic.otf",
      weight: "500",
      style: "italic"
    },
    {
      path: "./fonts/AA Stetica Bold.otf",
      weight: "700",
      style: "normal"
    },
    {
      path: "./fonts/AA Stetica Bold Italic.otf",
      weight: "700",
      style: "italic"
    },
    {
      path: "./fonts/AA Stetica Black_0.otf",
      weight: "900",
      style: "normal"
    }
  ],
  variable: "--font-aa-stetica",
  display: "swap"
});

const g8Display = localFont({
  src: [
    {
      path: "./fonts/G8-Bold.otf",
      weight: "700",
      style: "normal"
    },
    {
      path: "./fonts/G8-Italic.otf",
      weight: "700",
      style: "italic"
    }
  ],
  variable: "--font-g8-display",
  display: "swap"
});

function resolveInitialLocale(): Locale {
  const cookieStore = cookies();
  const localeFromCookie = cookieStore.get("portfolio-locale")?.value;
  if (localeFromCookie === "ru" || localeFromCookie === "en") {
    return localeFromCookie;
  }

  return "ru";
}

function resolveUrl(value?: string | null): URL | undefined {
  const normalizedValue = value?.trim();
  if (!normalizedValue) {
    return undefined;
  }

  try {
    return new URL(normalizedValue);
  } catch {
    try {
      return new URL(normalizedValue, env.siteUrl);
    } catch {
      return undefined;
    }
  }
}

async function resolveMetadataSettings() {
  try {
    return await getSiteSettings({ next: { revalidate: 60 } });
  } catch {
    return fallbackSettings;
  }
}

export async function generateMetadata(): Promise<Metadata> {
  const locale = resolveInitialLocale();
  const settings = await resolveMetadataSettings();
  const homepageContent = normalizeHomepageContent(settings.homepage_content);
  const siteMeta = homepageContent.site_meta;
  const title = pickLocalized(siteMeta, "title", locale) || pickLocalized(homepageContent, "brand_name", locale);
  const description = pickLocalized(siteMeta, "description", locale) || pickLocalized(settings, "hero_subtitle", locale);
  const openGraphTitle = pickLocalized(siteMeta, "og_title", locale) || title;
  const openGraphDescription = pickLocalized(siteMeta, "og_description", locale) || description;
  const siteName = pickLocalized(homepageContent, "brand_name", locale) || settings.brand_name;
  const metadataBase = resolveUrl(env.siteUrl);
  const canonical = resolveUrl(siteMeta.canonical_url);
  const openGraphImage = resolveUrl(siteMeta.og_image);

  return {
    metadataBase,
    title,
    description,
    keywords: siteMeta.keywords.length > 0 ? siteMeta.keywords : undefined,
    alternates: canonical
      ? {
          canonical,
        }
      : undefined,
    openGraph: {
      title: openGraphTitle,
      description: openGraphDescription,
      url: canonical,
      siteName,
      images: openGraphImage ? [{ url: openGraphImage }] : undefined,
      locale: locale === "ru" ? "ru_RU" : "en_US",
      type: "website",
    },
    twitter: {
      card: siteMeta.twitter_card,
      title: openGraphTitle,
      description: openGraphDescription,
      images: openGraphImage ? [openGraphImage] : undefined,
    },
    icons: {
      icon: [
        {
          url: "/favicon.svg",
          type: "image/svg+xml",
        },
      ],
      shortcut: ["/favicon.svg"],
      apple: [
        {
          url: "/apple-touch-icon.svg",
          type: "image/svg+xml",
        },
      ],
    },
    robots: {
      index: siteMeta.robots_index,
      follow: siteMeta.robots_follow,
      googleBot: {
        index: siteMeta.robots_index,
        follow: siteMeta.robots_follow,
      },
    },
  };
}

export async function generateViewport(): Promise<Viewport> {
  const settings = await resolveMetadataSettings();
  const siteMeta = normalizeHomepageContent(settings.homepage_content).site_meta;

  return {
    themeColor: siteMeta.theme_color,
  };
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const initialLocale = resolveInitialLocale();

  return (
    <html lang={initialLocale} suppressHydrationWarning>
      <head>
        <ColorSchemeScript />
      </head>
      <body className={`${aaStetica.variable} ${g8Display.variable} font-sans`}>
        <AppProviders initialLocale={initialLocale}>{children}</AppProviders>
      </body>
    </html>
  );
}
