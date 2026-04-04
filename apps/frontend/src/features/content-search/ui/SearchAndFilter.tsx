"use client";

import { SegmentedControl, TextInput } from "@mantine/core";

import { useI18n } from "@/shared/i18n/I18nProvider";

export function SearchAndFilter({
  query,
  onQueryChange,
  type,
  onTypeChange
}: {
  query: string;
  onQueryChange: (value: string) => void;
  type: string;
  onTypeChange: (value: string) => void;
}) {
  const { t } = useI18n();

  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <TextInput
        className="md:max-w-md"
        placeholder={t("search")}
        value={query}
        onChange={(event) => onQueryChange(event.currentTarget.value)}
      />
      <SegmentedControl
        value={type}
        onChange={onTypeChange}
        data={[
          { label: t("filterAll"), value: "all" },
          { label: t("filterArticles"), value: "article" },
          { label: t("filterVideos"), value: "video" }
        ]}
      />
    </div>
  );
}

