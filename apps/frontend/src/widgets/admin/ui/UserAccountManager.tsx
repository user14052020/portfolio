"use client";

import { PasswordInput } from "@mantine/core";
import { useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { changeCurrentUserPassword } from "@/shared/api/client";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

type PasswordForm = {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
};

const emptyPasswordForm: PasswordForm = {
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
};

export function UserAccountManager() {
  const { tokens, user } = useAdminAuth();
  const [form, setForm] = useState<PasswordForm>(emptyPasswordForm);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleSubmit() {
    if (!tokens?.access_token) {
      return;
    }
    const currentPassword = form.currentPassword;
    const newPassword = form.newPassword;
    const confirmPassword = form.confirmPassword;

    setNotice(null);
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError("Fill in all password fields.");
      return;
    }
    if (newPassword.length < 10) {
      setError("New password must be at least 10 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("New password confirmation does not match.");
      return;
    }

    setIsSaving(true);
    try {
      await changeCurrentUserPassword(
        {
          current_password: currentPassword,
          new_password: newPassword,
        },
        tokens.access_token,
      );
      setForm(emptyPasswordForm);
      setError(null);
      setNotice("Password changed.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to change password.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="space-y-7">
      <SectionHeader
        eyebrow="Account"
        title="User"
        description="Change the password for the current admin account."
      />

      <SurfaceCard
        variant="elevated"
        header={
          <SectionHeader
            eyebrow={user?.role.name ?? "admin"}
            title={user?.full_name ?? "Current user"}
            description={user?.email ?? "Authenticated account"}
            action={<PillBadge tone={user?.is_active ? "mint" : "neutral"}>{user?.is_active ? "active" : "inactive"}</PillBadge>}
          />
        }
      >
        <div className="grid gap-5 md:grid-cols-2">
          <PasswordInput
            label="Current password"
            value={form.currentPassword}
            onChange={(event) => setForm({ ...form, currentPassword: event.currentTarget.value })}
          />
          <div className="hidden md:block" />
          <PasswordInput
            label="New password"
            description="At least 10 characters."
            value={form.newPassword}
            onChange={(event) => setForm({ ...form, newPassword: event.currentTarget.value })}
          />
          <PasswordInput
            label="Confirm new password"
            value={form.confirmPassword}
            onChange={(event) => setForm({ ...form, confirmPassword: event.currentTarget.value })}
          />
        </div>

        {notice ? (
          <div className="mt-5 rounded-[20px] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            {notice}
          </div>
        ) : null}
        {error ? (
          <div className="mt-5 rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="mt-6 flex justify-end">
          <SoftButton tone="dark" onClick={() => void handleSubmit()} disabled={isSaving}>
            {isSaving ? "Changing..." : "Change password"}
          </SoftButton>
        </div>
      </SurfaceCard>
    </div>
  );
}
