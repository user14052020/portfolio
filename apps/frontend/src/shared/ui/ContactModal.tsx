"use client";

import { Modal } from "@mantine/core";

import { ContactForm } from "@/features/contact-request/ui/ContactForm";
import { useI18n } from "@/shared/i18n/I18nProvider";

export function ContactModal({
  opened,
  onClose
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const { t } = useI18n();

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      centered
      size="lg"
      radius="xl"
      title={<span className="text-lg font-semibold">{t("contactTitle")}</span>}
    >
      <p className="mb-6 text-sm text-slate-600">{t("contactDescription")}</p>
      <ContactForm onSuccess={onClose} />
    </Modal>
  );
}

