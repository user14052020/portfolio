"use client";

import { createContext, useContext, useEffect, useState } from "react";

import type { Locale } from "@/shared/api/types";
import { dictionaries, type DictionaryKey } from "@/shared/i18n/dictionaries";

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: DictionaryKey) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);
const STORAGE_KEY = "portfolio-locale";
const COOKIE_KEY = "portfolio-locale";
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

function persistLocale(locale: Locale) {
  window.localStorage.setItem(STORAGE_KEY, locale);
  document.cookie = `${COOKIE_KEY}=${locale}; path=/; max-age=${COOKIE_MAX_AGE_SECONDS}; samesite=lax`;
}

export function I18nProvider({
  children,
  initialLocale
}: {
  children: React.ReactNode;
  initialLocale: Locale;
}) {
  const [locale, setLocale] = useState<Locale>(initialLocale);

  useEffect(() => {
    persistLocale(locale);
  }, [locale]);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const handleSetLocale = (nextLocale: Locale) => {
    setLocale(nextLocale);
  };

  const value: I18nContextValue = {
    locale,
    setLocale: handleSetLocale,
    t: (key) => (dictionaries[locale] as Record<string, string>)[key] ?? dictionaries.en[key]
  };

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used inside I18nProvider");
  }
  return context;
}
