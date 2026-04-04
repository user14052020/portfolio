"use client";

import { Button, Stack, TextInput, Textarea } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";

import { createContactRequest } from "@/shared/api/client";
import { useI18n } from "@/shared/i18n/I18nProvider";

export function ContactForm({ onSuccess }: { onSuccess?: () => void }) {
  const { locale, t } = useI18n();
  const form = useForm({
    initialValues: {
      name: "",
      email: "",
      message: ""
    }
  });

  const handleSubmit = form.onSubmit(async (values) => {
    await createContactRequest({ ...values, locale, source_page: "home_modal" });
    notifications.show({
      title: t("contactSuccess"),
      message: locale === "ru" ? "Сообщение сохранено в CRM админки." : "Message stored in the admin CRM queue."
    });
    form.reset();
    onSuccess?.();
  });

  return (
    <form onSubmit={handleSubmit}>
      <Stack>
        <TextInput label={locale === "ru" ? "Имя" : "Name"} placeholder="Vadim" {...form.getInputProps("name")} />
        <TextInput
          label="Email"
          placeholder="hello@example.com"
          type="email"
          {...form.getInputProps("email")}
        />
        <Textarea
          label={locale === "ru" ? "Сообщение" : "Message"}
          minRows={5}
          placeholder={
            locale === "ru"
              ? "Опишите задачу, сроки и текущий статус проекта"
              : "Describe the scope, timeline and current stage of your project"
          }
          {...form.getInputProps("message")}
        />
        <Button type="submit" radius="xl" size="md">
          {t("submit")}
        </Button>
      </Stack>
    </form>
  );
}

