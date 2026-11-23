"""Serviços compartilhados pelas rotas (biblioteca, sessões e processamento de arquivos)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fastapi import Request

from gotcha.domain.models import ParsedBatch
from gotcha.importers import Source, get
from gotcha.sandbox import parse_isolated
from gotcha.storage.db import Database
from gotcha.storage.library import Library
from gotcha.storage.sessions import Sessions


@dataclass
class Services:
    library: Library
    sessions: Sessions
    sandbox: bool
    sandbox_timeout: float

    def parse(self, src: Source, importer: str) -> ParsedBatch:
        if self.sandbox:
            return parse_isolated(src, importer, timeout=self.sandbox_timeout)
        return get(importer).parse(src)


def build_services(
    data_dir: Path,
    clock: Callable[[], float] = time.time,
    sandbox: bool = True,
    sandbox_timeout: float = 120,
) -> Services:
    data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(data_dir / "gotcha.db")
    library = Library(db, clock)
    return Services(library, Sessions(db, library, clock), sandbox, sandbox_timeout)


def services(request: Request) -> Services:
    svc: Services = request.app.state.services
    return svc
