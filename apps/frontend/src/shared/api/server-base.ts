import { serverEnv } from "@/shared/config/server-env";
import {
  appendQueryParams,
  normalizePath,
  type RequestOptions,
  throwRequestError,
} from "@/shared/api/request-core";

export function buildServerUrl(path: string, query?: RequestOptions["query"]) {
  const normalizedPath = normalizePath(path);
  const baseUrl = serverEnv.internalApiUrl.trim();
  const url =
    baseUrl.startsWith("http://") || baseUrl.startsWith("https://")
      ? new URL(`${baseUrl}${normalizedPath}`)
      : new URL(`${baseUrl}${normalizedPath}`, serverEnv.siteUrl);

  return appendQueryParams(url, query).toString();
}

export async function requestFromServer<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  if (!isFormData && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const explicitToken = typeof options.token === "string" ? options.token.trim() : "";
  if (explicitToken) {
    headers.set("Authorization", `Bearer ${explicitToken}`);
  }

  const response = await fetch(buildServerUrl(path, options.query), {
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
