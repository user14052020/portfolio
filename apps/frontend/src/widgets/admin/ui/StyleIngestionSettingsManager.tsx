"use client";

import { Button, NumberInput, Stack, TextInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getStyleIngestionSettings, updateStyleIngestionSettings } from "@/shared/api/client";
import type { StyleIngestionRuntimeSettings } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

const DEFAULT_SOURCE_NAME = "aesthetics_wiki";

function toFiniteNumber(value: string | number, fallback: number) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return fallback;
}

export function StyleIngestionSettingsManager() {
  const { tokens } = useAdminAuth();
  const [settings, setSettings] = useState<StyleIngestionRuntimeSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }

    let cancelled = false;

    async function loadSettings() {
      try {
        const nextSettings = await getStyleIngestionSettings(DEFAULT_SOURCE_NAME, tokens.access_token);
        if (cancelled) {
          return;
        }
        setSettings(nextSettings);
        setError(null);
      } catch (nextError) {
        if (cancelled) {
          return;
        }
        setError(nextError instanceof Error ? nextError.message : "Failed to load parser timing settings");
      }
    }

    void loadSettings();
    return () => {
      cancelled = true;
    };
  }, [tokens?.access_token]);

  if (!tokens?.access_token) {
    return (
      <WindowFrame title="Parser timing settings" subtitle="Admin access required">
        <div className="text-sm text-slate-500">Sign in as admin to manage parser runtime timing.</div>
      </WindowFrame>
    );
  }

  if (!settings) {
    return (
      <WindowFrame title="Parser timing settings" subtitle="Manage ingestion pauses and worker intervals">
        <div className={error ? "text-sm text-rose-600" : "text-sm text-slate-500"}>
          {error ?? "Loading parser timing settings..."}
        </div>
      </WindowFrame>
    );
  }

  return (
    <WindowFrame
      title="Parser timing settings"
      subtitle="Manage crawl delays, cooldowns, retry jitter, and worker lease intervals"
    >
      <Stack>
        <TextInput label="Source name" value={settings.source_name} disabled />

        <div className="grid gap-4 md:grid-cols-2">
          <NumberInput
            label="Min delay, seconds"
            min={0}
            decimalScale={2}
            value={settings.min_delay_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? { ...current, min_delay_seconds: toFiniteNumber(value, current.min_delay_seconds) }
                  : current
              )
            }
          />
          <NumberInput
            label="Max delay, seconds"
            min={0}
            decimalScale={2}
            value={settings.max_delay_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? { ...current, max_delay_seconds: toFiniteNumber(value, current.max_delay_seconds) }
                  : current
              )
            }
          />
          <NumberInput
            label="Delay jitter ratio"
            min={0}
            max={1}
            step={0.05}
            decimalScale={2}
            value={settings.jitter_ratio}
            onChange={(value) =>
              setSettings((current) =>
                current ? { ...current, jitter_ratio: toFiniteNumber(value, current.jitter_ratio) } : current
              )
            }
          />
          <NumberInput
            label="Retry backoff, seconds"
            min={0}
            decimalScale={2}
            value={settings.retry_backoff_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? { ...current, retry_backoff_seconds: toFiniteNumber(value, current.retry_backoff_seconds) }
                  : current
              )
            }
          />
          <NumberInput
            label="Retry backoff jitter, seconds"
            min={0}
            decimalScale={2}
            value={settings.retry_backoff_jitter_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      retry_backoff_jitter_seconds: toFiniteNumber(value, current.retry_backoff_jitter_seconds)
                    }
                  : current
              )
            }
          />
          <NumberInput
            label="Worker idle sleep, seconds"
            min={0.1}
            decimalScale={2}
            value={settings.worker_idle_sleep_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      worker_idle_sleep_seconds: toFiniteNumber(value, current.worker_idle_sleep_seconds)
                    }
                  : current
              )
            }
          />
          <NumberInput
            label="Empty body cooldown min, seconds"
            min={0}
            decimalScale={2}
            value={settings.empty_body_cooldown_min_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      empty_body_cooldown_min_seconds: toFiniteNumber(
                        value,
                        current.empty_body_cooldown_min_seconds
                      )
                    }
                  : current
              )
            }
          />
          <NumberInput
            label="Empty body cooldown max, seconds"
            min={0}
            decimalScale={2}
            value={settings.empty_body_cooldown_max_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      empty_body_cooldown_max_seconds: toFiniteNumber(
                        value,
                        current.empty_body_cooldown_max_seconds
                      )
                    }
                  : current
              )
            }
          />
          <NumberInput
            label="Worker lease TTL, seconds"
            min={5}
            decimalScale={2}
            value={settings.worker_lease_ttl_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      worker_lease_ttl_seconds: toFiniteNumber(value, current.worker_lease_ttl_seconds)
                    }
                  : current
              )
            }
          />
          <NumberInput
            label="Worker lease heartbeat, seconds"
            min={1}
            decimalScale={2}
            value={settings.worker_lease_heartbeat_interval_seconds}
            onChange={(value) =>
              setSettings((current) =>
                current
                  ? {
                      ...current,
                      worker_lease_heartbeat_interval_seconds: toFiniteNumber(
                        value,
                        current.worker_lease_heartbeat_interval_seconds
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
              const updated = await updateStyleIngestionSettings(
                settings.source_name,
                {
                  min_delay_seconds: settings.min_delay_seconds,
                  max_delay_seconds: settings.max_delay_seconds,
                  jitter_ratio: settings.jitter_ratio,
                  empty_body_cooldown_min_seconds: settings.empty_body_cooldown_min_seconds,
                  empty_body_cooldown_max_seconds: settings.empty_body_cooldown_max_seconds,
                  retry_backoff_seconds: settings.retry_backoff_seconds,
                  retry_backoff_jitter_seconds: settings.retry_backoff_jitter_seconds,
                  worker_idle_sleep_seconds: settings.worker_idle_sleep_seconds,
                  worker_lease_ttl_seconds: settings.worker_lease_ttl_seconds,
                  worker_lease_heartbeat_interval_seconds: settings.worker_lease_heartbeat_interval_seconds
                },
                tokens.access_token
              );
              setSettings(updated);
              setError(null);
            } catch (nextError) {
              setError(nextError instanceof Error ? nextError.message : "Failed to save parser timing settings");
            } finally {
              setIsSaving(false);
            }
          }}
        >
          Save parser timing settings
        </Button>
      </Stack>
    </WindowFrame>
  );
}
