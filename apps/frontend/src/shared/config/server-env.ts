function normalizeEnvUrl(value: string | undefined, fallback: string) {
  const normalized = value?.trim();
  return normalized ? normalized : fallback;
}

export const serverEnv = {
  internalApiUrl: normalizeEnvUrl(process.env.INTERNAL_API_URL, "http://backend:8000/api/v1"),
  siteUrl: normalizeEnvUrl(process.env.NEXT_PUBLIC_SITE_URL, "http://localhost:3000"),
};
