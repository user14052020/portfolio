"use client";

import { Button, PasswordInput, Stack, TextInput } from "@mantine/core";
import { useForm } from "@mantine/form";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { useI18n } from "@/shared/i18n/I18nProvider";

export function LoginForm() {
  const { locale, t } = useI18n();
  const { login } = useAdminAuth();
  const form = useForm({
    initialValues: {
      email: "",
      password: ""
    }
  });

  const handleSubmit = form.onSubmit(async (values) => {
    await login(values.email, values.password);
    window.location.href = "/admin";
  });

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-md">
      <Stack>
        <TextInput label="Email" {...form.getInputProps("email")} />
        <PasswordInput label={locale === "ru" ? "Пароль" : "Password"} {...form.getInputProps("password")} />
        <Button type="submit" radius="xl" size="md">
          {t("adminLogin")}
        </Button>
      </Stack>
    </form>
  );
}

