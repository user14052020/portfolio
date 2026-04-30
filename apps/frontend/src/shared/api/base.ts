import { browserAdminTokenStore } from "@/shared/auth/adminTokenStore";
import {
  appendQueryParams,
  normalizePath,
  type RequestOptions,
  throwRequestError,
} from "@/shared/api/request-core";

const BROWSER_API_BASE_PATH = "/api/v1";

export function buildUrl(path: string, query?: RequestOptions["query"]) {
  if (typeof window === "undefined") {
    throw new Error("Browser API client cannot be used on the server.");
  }

  const normalizedPath = normalizePath(path);
  const url = new URL(`${BROWSER_API_BASE_PATH}${normalizedPath}`, window.location.origin);
  return appendQueryParams(url, query).toString();
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
    await throwRequestError(response);
  }

  if (response.status === 204) {
    return null as T;
  }

  return (await response.json()) as T;
}
