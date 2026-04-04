export const env = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  internalApiUrl: process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  mediaUrl: process.env.NEXT_PUBLIC_MEDIA_URL ?? "http://localhost:8000/media",
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"
};
