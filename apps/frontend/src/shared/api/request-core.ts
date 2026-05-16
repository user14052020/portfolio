export type RequestOptions = RequestInit & {
  token?: string;
  useStoredAuth?: boolean;
  query?: Record<string, string | number | boolean | undefined | null>;
  next?: {
    revalidate?: number | false;
    tags?: string[];
  };
};

export function normalizePath(path: string) {
  return path.startsWith("/") ? path : `/${path}`;
}

export function appendQueryParams(url: URL, query?: RequestOptions["query"]) {
  if (!query) {
    return url;
  }

  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  return url;
}

export async function throwRequestError(response: Response): Promise<never> {
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
