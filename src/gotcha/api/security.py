"""Segurança de um servidor local: só localhost, sem requisições de outros sites do navegador."""

from __future__ import annotations

from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-gotcha"

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


def hostname(host_header: str) -> str:
    value = host_header.strip()
    if value.startswith("["):  # IPv6: [::1]:8765
        return value[1:].split("]")[0]
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


class LocalOnlyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if hostname(request.headers.get("host", "")) not in ALLOWED_HOSTS:
            return PlainTextResponse("Host não permitido.", status_code=400)
        if request.method not in SAFE_METHODS:
            if request.headers.get(CSRF_HEADER) != "1":
                return PlainTextResponse("Cabeçalho de proteção ausente.", status_code=403)
            origin = request.headers.get("origin")
            if origin and (urlsplit(origin).hostname or "") not in ALLOWED_HOSTS:
                return PlainTextResponse("Origem não permitida.", status_code=403)
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Content-Security-Policy", CSP)
        return response
