"use client";

import { Button, NumberInput, Stack } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getStylistRuntimeSettings, updateStylistRuntimeSettings } from "@/shared/api/client";
import type { StylistRuntimeSettings } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

const MAX_DAILY_GENERATION_LIMIT_NON_ADMIN = 1000;
const MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN = 86_400;
const MAX_MESSAGE_COOLDOWN_SECONDS = 3_600;
const MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS = 3_600;

function toBoundedInteger(value: string | number, fallback: number, min: number, max: number) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.min(Math.max(Math.round(value), min), max);
  }
  return fallback;
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

  if (!tokens?.access_token) {
    return (
      <WindowFrame title="Stylist Chat Runtime Settings" subtitle="Admin access required">
        <div className="text-sm text-slate-500">Sign in as admin to manage non-admin limits and cooldowns.</div>
      </WindowFrame>
    );
  }

  if (!settings) {
    return (
      <WindowFrame title="Stylist Chat Runtime Settings" subtitle="Manage non-admin limits and cooldowns">
        <div className={error ? "text-sm text-rose-600" : "text-sm text-slate-500"}>
          {error ?? "Loading stylist runtime settings..."}
        </div>
      </WindowFrame>
    );
  }

  return (
    <WindowFrame title="Stylist Chat Runtime Settings" subtitle="Manage non-admin limits and cooldowns">
      <Stack>
        <div className="grid gap-4 md:grid-cols-2">
          <NumberInput
            label="Daily generation limit (non-admin)"
            min={0}
            max={MAX_DAILY_GENERATION_LIMIT_NON_ADMIN}
            value={settings.daily_generation_limit_non_admin}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      daily_generation_limit_non_admin: toBoundedInteger(
                        value,
                        current.daily_generation_limit_non_admin,
                        0,
                        MAX_DAILY_GENERATION_LIMIT_NON_ADMIN
                      )
                    }
                  : current
              )
            }
          />
          <NumberInput
            label="Daily text chat duration limit, seconds (non-admin)"
            min={0}
            max={MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN}
            value={settings.daily_chat_seconds_limit_non_admin}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      daily_chat_seconds_limit_non_admin: toBoundedInteger(
                        value,
                        current.daily_chat_seconds_limit_non_admin,
                        0,
                        MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN
                      )
                    }
                  : current
              )
            }
          />
          <NumberInput
            label="Message cooldown, seconds"
            min={0}
            max={MAX_MESSAGE_COOLDOWN_SECONDS}
            value={settings.message_cooldown_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      message_cooldown_seconds: toBoundedInteger(
                        value,
                        current.message_cooldown_seconds,
                        0,
                        MAX_MESSAGE_COOLDOWN_SECONDS
                      )
                    }
                  : current
              )
            }
          />
          <NumberInput
            label="Try other style cooldown, seconds"
            min={0}
            max={MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS}
            value={settings.try_other_style_cooldown_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      try_other_style_cooldown_seconds: toBoundedInteger(
                        value,
                        current.try_other_style_cooldown_seconds,
                        0,
                        MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS
                      )
                    }
                  : current
              )
            }
          />
        </div>

        {error ? <div className="text-sm text-rose-600">{error}</div> : null}

        <Button
          radius="xl"
          loading={isSaving}
          onClick={async () => {
            if (!tokens?.access_token || !settings) {
              return;
            }
            setIsSaving(true);
            try {
              const updated = await updateStylistRuntimeSettings(
                {
                  daily_generation_limit_non_admin: settings.daily_generation_limit_non_admin,
                  daily_chat_seconds_limit_non_admin: settings.daily_chat_seconds_limit_non_admin,
                  message_cooldown_seconds: settings.message_cooldown_seconds,
                  try_other_style_cooldown_seconds: settings.try_other_style_cooldown_seconds
                },
                tokens.access_token
              );
              setSettings(updated);
              setError(null);
            } catch (nextError) {
              setError(nextError instanceof Error ? nextError.message : "Failed to save stylist runtime settings");
            } finally {
              setIsSaving(false);
            }
          }}
        >
          Save settings
        </Button>
      </Stack>
    </WindowFrame>
  );
}
