"use client";

import { MantineProvider, createTheme } from "@mantine/core";
import { Notifications } from "@mantine/notifications";

import type { Locale } from "@/shared/api/types";
import { I18nProvider } from "@/shared/i18n/I18nProvider";

const theme = createTheme({
  primaryColor: "orange",
  fontFamily: "var(--font-aa-stetica)",
  headings: {
    fontFamily: "var(--font-aa-stetica)"
  },
  defaultRadius: "md"
});

export function AppProviders({
  children,
  initialLocale
}: {
  children: React.ReactNode;
  initialLocale: Locale;
}) {
  return (
    <MantineProvider theme={theme}>
      <Notifications />
      <I18nProvider initialLocale={initialLocale}>{children}</I18nProvider>
    </MantineProvider>
  );
}
