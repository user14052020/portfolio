import { proxyBackendRequest } from "@/shared/api/backend-proxy";

type RouteContext = {
  params: {
    path?: string[];
  };
};

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function handle(request: Request, context: RouteContext) {
  return proxyBackendRequest(request, "/media", context.params.path ?? []);
}

export const GET = handle;
export const HEAD = handle;
