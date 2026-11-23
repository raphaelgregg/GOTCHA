"""Fábrica da aplicação FastAPI: API, segurança local e interface web estática."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from gotcha.storage.sessions import SessionFinished, TimeExpired

from . import routes_library, routes_sessions
from .security import LocalOnlyMiddleware
from .services import build_services


def create_app(
    data_dir: Path,
    clock: Callable[[], float] = time.time,
    sandbox: bool = True,
    static_dir: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="GOTCHA", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.services = build_services(data_dir, clock, sandbox)
    app.add_middleware(LocalOnlyMiddleware)

    def error(status: int) -> Callable[[Request, Exception], JSONResponse]:
        def handler(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse({"detail": str(exc.args[0] if exc.args else exc)}, status_code=status)

        return handler

    app.add_exception_handler(KeyError, lambda _r, _e: JSONResponse({"detail": "Não encontrado."}, 404))
    app.add_exception_handler(ValueError, error(400))
    app.add_exception_handler(TimeExpired, error(409))
    app.add_exception_handler(SessionFinished, error(409))
    app.include_router(routes_library.router)
    app.include_router(routes_sessions.router)
    if static_dir is not None and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="web")
    return app
