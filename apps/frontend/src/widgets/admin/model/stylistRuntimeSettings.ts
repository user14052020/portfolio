import type { StylistRuntimeSettings } from "@/shared/api/types";

export const MAX_DAILY_GENERATION_LIMIT_NON_ADMIN = 1000;
export const MAX_DAILY_CHAT_SECONDS_LIMIT_NON_ADMIN = 86_400;
export const MAX_MESSAGE_COOLDOWN_SECONDS = 3_600;
export const MAX_TRY_OTHER_STYLE_COOLDOWN_SECONDS = 3_600;

export type StylistRuntimeSettingsUpdatePayload = Pick<
  StylistRuntimeSettings,
  | "daily_generation_limit_non_admin"
  | "daily_chat_seconds_limit_non_admin"
  | "message_cooldown_seconds"
  | "try_other_style_cooldown_seconds"
>;

export function toBoundedInteger(value: string | number, fallback: number, min: number, max: number) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return Math.min(Math.max(Math.round(value), min), max);
  }
  return fallback;
}

export function buildStylistRuntimeSettingsUpdatePayload(
  settings: StylistRuntimeSettings
): StylistRuntimeSettingsUpdatePayload {
  return {
    daily_generation_limit_non_admin: settings.daily_generation_limit_non_admin,
    daily_chat_seconds_limit_non_admin: settings.daily_chat_seconds_limit_non_admin,
    message_cooldown_seconds: settings.message_cooldown_seconds,
    try_other_style_cooldown_seconds: settings.try_other_style_cooldown_seconds,
  };
}
