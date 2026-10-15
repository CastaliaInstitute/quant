"""Cloudflare Python Worker for bounded, stateless QuantLab lesson cells."""
import json

from workers import Response, WorkerEntrypoint

from safe_kernel import CellRejected, execute_cells

ALLOWED_ORIGINS = {
    "https://quant.castalia.institute",
    "https://quantlab.pages.dev",
    "http://localhost:8000",
}


def response(body, status=200, origin=None):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Vary": "Origin",
    }
    if origin in ALLOWED_ORIGINS:
        headers["Access-Control-Allow-Origin"] = origin
    return Response.new(json.dumps(body), {"status": status, "headers": headers})


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = request.url
        origin = request.headers.get("Origin")
        if request.method == "OPTIONS":
            if origin not in ALLOWED_ORIGINS:
                return response({"error": "Origin not allowed"}, 403)
            return Response.new("", {"status": 204, "headers": {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Max-Age": "86400",
                "Vary": "Origin",
            }})
        if url.endswith("/health") and request.method == "GET":
            return response({"status": "ok", "runtime": "bounded-python-cells"}, 200, origin)
        if not url.endswith("/execute") or request.method != "POST":
            return response({"error": "Use POST /execute"}, 404, origin)
        if origin not in ALLOWED_ORIGINS:
            return response({"error": "Origin not allowed"}, 403)
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > 24_000:
            return response({"error": "Request body is too large"}, 413, origin)
        try:
            payload = await request.json()
            outputs = execute_cells(payload.get("cells"))
        except CellRejected as error:
            return response({"error": str(error)}, 400, origin)
        except Exception:
            return response({"error": "Malformed JSON request"}, 400, origin)
        return response({"outputs": outputs}, 200, origin)
