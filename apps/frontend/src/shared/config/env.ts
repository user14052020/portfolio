function normalizeEnvUrl(value: string | undefined, fallback: string) {
  const normalized = value?.trim();
  return normalized ? normalized : fallback;
}

export const env = {
  mediaUrl: normalizeEnvUrl(process.env.NEXT_PUBLIC_MEDIA_URL, "/media"),
  siteUrl: normalizeEnvUrl(process.env.NEXT_PUBLIC_SITE_URL, "http://localhost:3000"),
};
