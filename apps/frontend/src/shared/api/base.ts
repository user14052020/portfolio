import { env } from "@/shared/config/env";
import { browserAdminTokenStore } from "@/shared/auth/adminTokenStore";

export type RequestOptions = RequestInit & {
  token?: string;
  useStoredAuth?: boolean;
  query?: Record<string, string | number | boolean | undefined | null>;
  next?: {
    revalidate?: number | false;
    tags?: string[];
  };
};

export function buildUrl(path: string, query?: RequestOptions["query"]) {

  const baseUrl = env.apiUrl;

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  const url =

    baseUrl.startsWith("http://") || baseUrl.startsWith("https://")

      ? new URL(`${baseUrl}${normalizedPath}`)

      : new URL(`${baseUrl}${normalizedPath}`, window.location.origin);

  if (query) {

    Object.entries(query).forEach(([key, value]) => {

      if (value !== undefined && value !== null && value !== "") {

        url.searchParams.set(key, String(value));

      }

    });

  }

  return url.toString();

}
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  if (!isFormData && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const explicitToken = typeof options.token === "string" ? options.token.trim() : "";
  if (explicitToken) {
    headers.set("Authorization", `Bearer ${explicitToken}`);
  } else if (options.useStoredAuth !== false && !headers.has("Authorization")) {
    const storedToken = browserAdminTokenStore.getAccessToken();
    if (storedToken) {
      headers.set("Authorization", `Bearer ${storedToken}`);
    }
  }

  const response = await fetch(buildUrl(path, options.query), {
    ...options,
    headers,
    cache: options.cache ?? "no-store",
    next: options.next,
  });

  if (!response.ok) {
    const text = await response.text();
    let payload: { detail?: unknown } | null = null;
    try {
      payload = JSON.parse(text) as { detail?: unknown };
    } catch {
      payload = null;
    }

    if (payload) {
      const detail =
        typeof payload.detail === "string"
          ? payload.detail
          : payload.detail && typeof payload.detail === "object" && "message" in payload.detail
            ? String((payload.detail as { message?: unknown }).message ?? "").trim()
            : "";
      const error = new Error(
        detail || text || `API request failed with status ${response.status}`
      ) as Error & { status?: number; payload?: unknown };
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    throw new Error(text || `API request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
}
