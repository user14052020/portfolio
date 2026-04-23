"use client";

import { NumberInput } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getStyleIngestionSettings, updateStyleIngestionSettings } from "@/shared/api/client";
import type { StyleIngestionRuntimeSettings } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import {
  buildStyleIngestionSettingsUpdatePayload,
  STYLE_INGESTION_SOURCE_NAME,
  type StyleIngestionNumberField,
  toFiniteNumber,
} from "@/widgets/admin/model/styleIngestionSettings";

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
        const nextSettings = await getStyleIngestionSettings(STYLE_INGESTION_SOURCE_NAME, tokens.access_token);
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

  function updateParserField(field: StyleIngestionNumberField, value: string | number) {
    setSettings((current) =>
      current
        ? {
            ...current,
            [field]: toFiniteNumber(value, current[field]),
          }
        : current,
    );
  }

  async function handleSave() {
    if (!tokens?.access_token || !settings) {
      return;
    }
    setIsSaving(true);
    try {
      const updated = await updateStyleIngestionSettings(
        settings.source_name,
        buildStyleIngestionSettingsUpdatePayload(settings),
        tokens.access_token,
      );
      setSettings(updated);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save parser timing settings");
    } finally {
      setIsSaving(false);
    }
  }

  if (!tokens?.access_token) {
    return (
      <SurfaceCard variant="soft">
        <ParserTimingHeader />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Sign in as admin to manage parser runtime timing.
        </p>
      </SurfaceCard>
    );
  }

  if (!settings) {
    return (
      <SurfaceCard variant="soft">
        <ParserTimingHeader />
        <p className={error ? "mt-4 text-sm text-rose-700" : "mt-4 text-sm text-[var(--text-secondary)]"}>
          {error ?? "Loading parser timing settings..."}
        </p>
      </SurfaceCard>
    );
  }

  return (
    <SurfaceCard
      variant="elevated"
      header={
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <ParserTimingHeader />
          <SoftButton tone="dark" onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save parser timing"}
          </SoftButton>
        </div>
      }
    >
      <div className="space-y-5">
        <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">Source</p>
          <p className="mt-2 font-mono text-sm text-[var(--text-primary)]">{settings.source_name}</p>
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <ParserNumberControl
            label="Min delay"
            description="Lower bound between source requests."
            value={settings.min_delay_seconds}
            meta="seconds"
            onChange={(value) => updateParserField("min_delay_seconds", value)}
          />
          <ParserNumberControl
            label="Max delay"
            description="Upper bound for polite crawl spacing."
            value={settings.max_delay_seconds}
            meta="seconds"
            onChange={(value) => updateParserField("max_delay_seconds", value)}
          />
          <ParserNumberControl
            label="Delay jitter"
            description="Randomized ratio applied to request spacing."
            value={settings.jitter_ratio}
            max={1}
            step={0.05}
            meta="0-1"
            onChange={(value) => updateParserField("jitter_ratio", value)}
          />
          <ParserNumberControl
            label="Retry backoff"
            description="Base wait after a failed source request."
            value={settings.retry_backoff_seconds}
            meta="seconds"
            onChange={(value) => updateParserField("retry_backoff_seconds", value)}
          />
          <ParserNumberControl
            label="Retry jitter"
            description="Extra randomized wait for retries."
            value={settings.retry_backoff_jitter_seconds}
            meta="seconds"
            onChange={(value) => updateParserField("retry_backoff_jitter_seconds", value)}
          />
          <ParserNumberControl
            label="Worker idle sleep"
            description="Pause before polling an empty queue again."
            value={settings.worker_idle_sleep_seconds}
            min={0.1}
            meta="seconds"
            onChange={(value) => updateParserField("worker_idle_sleep_seconds", value)}
          />
          <ParserNumberControl
            label="Empty body cooldown min"
            description="Minimum cooldown after an empty source response."
            value={settings.empty_body_cooldown_min_seconds}
            meta="seconds"
            onChange={(value) => updateParserField("empty_body_cooldown_min_seconds", value)}
          />
          <ParserNumberControl
            label="Empty body cooldown max"
            description="Maximum cooldown after an empty source response."
            value={settings.empty_body_cooldown_max_seconds}
            meta="seconds"
            onChange={(value) => updateParserField("empty_body_cooldown_max_seconds", value)}
          />
          <ParserNumberControl
            label="Worker lease TTL"
            description="How long a worker lease remains valid."
            value={settings.worker_lease_ttl_seconds}
            min={5}
            meta="seconds"
            onChange={(value) => updateParserField("worker_lease_ttl_seconds", value)}
          />
          <ParserNumberControl
            label="Lease heartbeat"
            description="Interval for keeping an active worker lease alive."
            value={settings.worker_lease_heartbeat_interval_seconds}
            min={1}
            meta="seconds"
            onChange={(value) => updateParserField("worker_lease_heartbeat_interval_seconds", value)}
          />
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <ParserMetric
            label="Crawl window"
            value={`${formatSeconds(settings.min_delay_seconds)}-${formatSeconds(settings.max_delay_seconds)}`}
          />
          <ParserMetric label="Retry base" value={formatSeconds(settings.retry_backoff_seconds)} />
          <ParserMetric label="Idle poll" value={formatSeconds(settings.worker_idle_sleep_seconds)} />
          <ParserMetric label="Lease TTL" value={formatSeconds(settings.worker_lease_ttl_seconds)} />
        </div>

        {error ? (
          <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>
        ) : null}
      </div>
    </SurfaceCard>
  );
}

function ParserTimingHeader() {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <PillBadge tone="dark">Parser runtime</PillBadge>
        <PillBadge tone="accent">Aesthetics wiki</PillBadge>
      </div>
      <div>
        <h2 className="font-display text-2xl text-[var(--text-primary)]">Parser timing settings</h2>
        <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
          Manage crawl delays, cooldowns, retry jitter, and worker lease intervals from one admin surface.
        </p>
      </div>
    </div>
  );
}

function ParserNumberControl({
  label,
  description,
  value,
  min = 0,
  max,
  step,
  meta,
  onChange,
}: {
  label: string;
  description: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  meta: string;
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
          {meta}
        </PillBadge>
      </div>
      <NumberInput
        min={min}
        max={max}
        step={step}
        decimalScale={2}
        value={value}
        onChange={onChange}
      />
    </div>
  );
}

function ParserMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[22px] border border-[var(--border-soft)] bg-white/70 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{value}</p>
    </div>
  );
}
