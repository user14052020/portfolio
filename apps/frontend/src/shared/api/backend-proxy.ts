import { serverEnv } from "@/shared/config/server-env";

const HOP_BY_HOP_HEADERS = new Set([
  "accept-encoding",
  "connection",
  "content-encoding",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function getBackendOrigin() {
  return serverEnv.internalApiUrl.trim().replace(/\/api\/v1\/?$/, "");
}

function normalizeSegments(path: string[]) {
  return path
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map(encodeURIComponent)
    .join("/");
}

function copyHeaders(source: Headers) {
  const headers = new Headers();
  source.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  return headers;
}

export function buildBackendProxyUrl(prefix: "/api/v1" | "/media", path: string[], search: string) {
  const normalizedPath = normalizeSegments(path);
  const target = new URL(`${getBackendOrigin()}${prefix}${normalizedPath ? `/${normalizedPath}` : ""}`);
  if (search) {
    target.search = search;
  }
  return target;
}

export async function proxyBackendRequest(
  request: Request,
  prefix: "/api/v1" | "/media",
  path: string[]
) {
  const incomingUrl = new URL(request.url);
  const targetUrl = buildBackendProxyUrl(prefix, path, incomingUrl.search);
  const headers = copyHeaders(request.headers);
  const method = request.method.toUpperCase();

  const response = await fetch(targetUrl, {
    method,
    headers,
    body: method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer(),
    cache: "no-store",
    redirect: "follow",
  });

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: copyHeaders(response.headers),
  });
}
