const isBrowser = typeof window !== "undefined";

export const env = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "/api/v1",


  internalApiUrl: process.env.NEXT_PUBLIC_API_URL ?? "/api/v1",

  mediaUrl: process.env.NEXT_PUBLIC_MEDIA_URL ?? "/media",
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
};