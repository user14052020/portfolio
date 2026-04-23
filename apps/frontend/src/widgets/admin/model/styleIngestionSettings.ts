import type { StyleIngestionRuntimeSettings } from "@/shared/api/types";

export const STYLE_INGESTION_SOURCE_NAME = "aesthetics_wiki";

export type StyleIngestionNumberField =
  | "min_delay_seconds"
  | "max_delay_seconds"
  | "jitter_ratio"
  | "empty_body_cooldown_min_seconds"
  | "empty_body_cooldown_max_seconds"
  | "retry_backoff_seconds"
  | "retry_backoff_jitter_seconds"
  | "worker_idle_sleep_seconds"
  | "worker_lease_ttl_seconds"
  | "worker_lease_heartbeat_interval_seconds";

export function toFiniteNumber(value: string | number, fallback: number) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  return fallback;
}

export function buildStyleIngestionSettingsUpdatePayload(settings: StyleIngestionRuntimeSettings) {
  return {
    min_delay_seconds: settings.min_delay_seconds,
    max_delay_seconds: settings.max_delay_seconds,
    jitter_ratio: settings.jitter_ratio,
    empty_body_cooldown_min_seconds: settings.empty_body_cooldown_min_seconds,
    empty_body_cooldown_max_seconds: settings.empty_body_cooldown_max_seconds,
    retry_backoff_seconds: settings.retry_backoff_seconds,
    retry_backoff_jitter_seconds: settings.retry_backoff_jitter_seconds,
    worker_idle_sleep_seconds: settings.worker_idle_sleep_seconds,
    worker_lease_ttl_seconds: settings.worker_lease_ttl_seconds,
    worker_lease_heartbeat_interval_seconds: settings.worker_lease_heartbeat_interval_seconds,
  };
}
