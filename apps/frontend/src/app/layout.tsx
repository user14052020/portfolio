import type { Metadata } from "next";
import { ColorSchemeScript } from "@mantine/core";
import { cookies, headers } from "next/headers";
import localFont from "next/font/local";

import type { Locale } from "@/shared/api/types";
import { AppProviders } from "@/providers/AppProviders";
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

export const metadata: Metadata = {
  title: "Creative full-stack portfolio with AI stylist",
  description: "Portfolio, blog, admin panel and AI stylist integration powered by FastAPI and Next.js."
};

function resolveInitialLocale(): Locale {
  const cookieStore = cookies();
  const localeFromCookie = cookieStore.get("portfolio-locale")?.value;
  if (localeFromCookie === "ru" || localeFromCookie === "en") {
    return localeFromCookie;
  }

  const acceptLanguage = headers().get("accept-language")?.toLowerCase() ?? "";
  return acceptLanguage.includes("ru") ? "ru" : "en";
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
