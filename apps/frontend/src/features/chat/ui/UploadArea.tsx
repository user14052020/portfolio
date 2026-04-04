"use client";

import { ActionIcon, Loader } from "@mantine/core";
import { IconPaperclip } from "@tabler/icons-react";

import { useI18n } from "@/shared/i18n/I18nProvider";

export function UploadArea({
  onSelect,
  isLoading,
  filename
}: {
  onSelect: (file: File) => void;
  isLoading: boolean;
  filename?: string;
}) {
  const { locale } = useI18n();

  return (
    <label className="flex self-end items-center">
      <ActionIcon
        component="span"
        radius={0}
        size="lg"
        variant="subtle"
        color="gray"
        title={filename ?? (locale === "ru" ? "Прикрепить файл" : "Attach file")}
        className={
          filename
            ? "h-11 w-11 rounded-none border border-slate-900 bg-slate-900 text-white transition hover:bg-slate-800"
            : "h-11 w-11 rounded-none border border-slate-200 bg-white text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
        }
      >
        {isLoading ? <Loader size={16} color="gray" /> : <IconPaperclip size={18} />}
      </ActionIcon>
      <input
        type="file"
        accept="image/*,video/*"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            onSelect(file);
          }
        }}
      />
    </label>
  );
}
