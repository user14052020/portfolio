"use client";

import { NumberInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getStylistRuntimeSettings, updateStylistRuntimeSettings } from "@/shared/api/browser-client";
import type { StylistRuntimeSettings } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import {
  buildStylistRuntimeSettingsUpdatePayload,
  MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN,
  MAX_DAILY_GENERATION_LIMIT_NON_ADMIN,
  MAX_MESSAGE_COOLDOWN_SECONDS,
  MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS,
  toBoundedInteger,
} from "@/widgets/admin/model/stylistRuntimeSettings";

type RuntimeField =
  | "daily_generation_limit_non_admin"
  | "daily_chat_seconds_limit_non_admin"
  | "message_cooldown_seconds"
  | "try_other_style_cooldown_seconds";

function formatSeconds(seconds: number) {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m`;
  }
  return `${Math.round(minutes / 60)}h`;
}

export function StylistRuntimeSettingsManager() {
  const { tokens } = useAdminAuth();
  const [settings, setSettings] = useState<StylistRuntimeSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }

    let cancelled = false;

    async function loadSettings() {
      try {
        const nextSettings = await getStylistRuntimeSettings(tokens.access_token);
        if (cancelled) {
          return;
        }
        setSettings(nextSettings);
        setError(null);
      } catch (nextError) {
        if (cancelled) {
          return;
        }
        setError(nextError instanceof Error ? nextError.message : "Failed to load stylist runtime settings");
      }
    }

    void loadSettings();
    return () => {
      cancelled = true;
    };
  }, [tokens?.access_token]);

  function updateRuntimeField(field: RuntimeField, value: string | number, min: number, max: number) {
    setSettings((current) =>
      current
        ? {
            ...current,
            [field]: toBoundedInteger(value, current[field], min, max),
          }
        : current
    );
  }

  async function handleSave() {
    if (!tokens?.access_token || !settings) {
      return;
    }
    setIsSaving(true);
    try {
      const updated = await updateStylistRuntimeSettings(
        buildStylistRuntimeSettingsUpdatePayload(settings),
        tokens.access_token
      );
      setSettings(updated);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save stylist runtime settings");
    } finally {
      setIsSaving(false);
    }
  }

  if (!tokens?.access_token) {
    return (
      <SurfaceCard variant="soft">
        <RuntimeHeader />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Sign in as admin to manage non-admin limits and cooldowns.
        </p>
      </SurfaceCard>
    );
  }

  if (!settings) {
    return (
      <SurfaceCard variant="soft">
        <RuntimeHeader />
        <p className={error ? "mt-4 text-sm text-rose-700" : "mt-4 text-sm text-[var(--text-secondary)]"}>
          {error ?? "Loading stylist runtime settings..."}
        </p>
      </SurfaceCard>
    );
  }

  return (
    <SurfaceCard
      variant="elevated"
      header={
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <RuntimeHeader />
          <SoftButton tone="dark" onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save runtime policy"}
          </SoftButton>
        </div>
      }
    >
      <div className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <RuntimeNumberControl
            label="Daily generations"
            description="Images per non-admin user/session per day."
            value={settings.daily_generation_limit_non_admin}
            max={MAX_DAILY_GENERATION_LIMIT_NON_ADMIN}
            onChange={(value) =>
              updateRuntimeField("daily_generation_limit_non_admin", value, 0, MAX_DAILY_GENERATION_LIMIT_NON_ADMIN)
            }
          />
          <RuntimeNumberControl
            label="Daily chat budget"
            description={`Text-chat seconds per day. Current: ${formatSeconds(settings.daily_chat_seconds_limit_non_admin)}.`}
            value={settings.daily_chat_seconds_limit_non_admin}
            max={MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN}
            onChange={(value) =>
              updateRuntimeField(
                "daily_chat_seconds_limit_non_admin",
                value,
                0,
                MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN
              )
            }
          />
          <RuntimeNumberControl
            label="Message cooldown"
            description={`Delay between messages. Current: ${formatSeconds(settings.message_cooldown_seconds)}.`}
            value={settings.message_cooldown_seconds}
            max={MAX_MESSAGE_COOLDOWN_SECONDS}
            onChange={(value) =>
              updateRuntimeField("message_cooldown_seconds", value, 0, MAX_MESSAGE_COOLDOWN_SECONDS)
            }
          />
          <RuntimeNumberControl
            label="Try other style cooldown"
            description={`Delay between style rerolls. Current: ${formatSeconds(settings.try_other_style_cooldown_seconds)}.`}
            value={settings.try_other_style_cooldown_seconds}
            max={MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS}
            onChange={(value) =>
              updateRuntimeField(
                "try_other_style_cooldown_seconds",
                value,
                0,
                MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS
              )
            }
          />
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <RuntimeMetric label="Generations" value={String(settings.daily_generation_limit_non_admin)} />
          <RuntimeMetric label="Chat budget" value={formatSeconds(settings.daily_chat_seconds_limit_non_admin)} />
          <RuntimeMetric label="Message gap" value={formatSeconds(settings.message_cooldown_seconds)} />
          <RuntimeMetric label="Style reroll gap" value={formatSeconds(settings.try_other_style_cooldown_seconds)} />
        </div>

        {error ? (
          <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>
        ) : null}
      </div>
    </SurfaceCard>
  );
}

function RuntimeHeader() {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <PillBadge tone="dark">Stylist runtime</PillBadge>
        <PillBadge tone="accent">Non-admin policy</PillBadge>
      </div>
      <div>
        <h2 className="font-display text-2xl text-[var(--text-primary)]">Chat limits and cooldowns</h2>
        <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
          Tune usage boundaries for the public stylist flow without changing admin access.
        </p>
      </div>
    </div>
  );
}

function RuntimeNumberControl({
  label,
  description,
  value,
  max,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  max: number;
  onChange: (value: string | number) => void;
}) {
  return (
    <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
          <p className="mt-1 text-xs leading-5 text-[var(--text-secondary)]">{description}</p>
        </div>
        <PillBadge tone="subtle" size="sm">
          max {max}
        </PillBadge>
      </div>
      <NumberInput min={0} max={max} value={value} onChange={onChange} />
    </div>
  );
}

function RuntimeMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[22px] border border-[var(--border-soft)] bg-white/70 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{value}</p>
    </div>
  );
}
