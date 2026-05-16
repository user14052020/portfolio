import { proxyBackendRequest } from "@/shared/api/backend-proxy";

type RouteContext = {
  params: {
    path?: string[];
  };
};

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function handle(request: Request, context: RouteContext) {
  return proxyBackendRequest(request, "/api/v1", context.params.path ?? []);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const HEAD = handle;
export const OPTIONS = handle;
