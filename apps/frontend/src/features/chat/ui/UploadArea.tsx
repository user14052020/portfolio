"use client";

import { Loader } from "@mantine/core";
import { IconPaperclip } from "@tabler/icons-react";

import { useI18n } from "@/shared/i18n/I18nProvider";
import { RoundIconButton } from "@/shared/ui/RoundIconButton";

export function UploadArea({
  onSelect,
  isLoading,
  filename,
  disabled = false
}: {
  onSelect: (file: File) => void;
  isLoading: boolean;
  filename?: string;
  disabled?: boolean;
}) {
  const { locale } = useI18n();

  return (
    <label className="flex self-end items-center">
      <RoundIconButton
        as="span"
        tone={filename ? "active" : "default"}
        title={
          filename ??
          (locale === "ru"
            ? "\u041f\u0440\u0438\u043a\u0440\u0435\u043f\u0438\u0442\u044c \u0444\u043e\u0442\u043e \u0432\u0435\u0449\u0438"
            : "Attach garment photo")
        }
        disabled={disabled || isLoading}
      >
        {isLoading ? <Loader size={16} color="gray" /> : <IconPaperclip size={18} />}
      </RoundIconButton>
      <input
        type="file"
        accept="image/*"
        className="hidden"
        disabled={disabled || isLoading}
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
