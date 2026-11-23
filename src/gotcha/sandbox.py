"""Execução isolada de importadores: subprocesso com tempo e memória limitados e sem rede.

É uma proteção de melhor esforço para arquivos não confiáveis (não substitui um sandbox de SO).
"""

from __future__ import annotations

import importlib
import multiprocessing as mp
import socket
import sys
from multiprocessing.connection import Connection
from typing import Any

from gotcha.domain.models import ParsedBatch
from gotcha.importers import Source, get


class SandboxError(RuntimeError):
    pass


class SandboxTimeout(SandboxError):
    pass


class NetworkBlocked(OSError):
    pass


def _block_network() -> None:
    def refuse(*_: Any, **__: Any) -> Any:
        raise NetworkBlocked("acesso à rede bloqueado no sandbox")

    socket.socket = refuse  # type: ignore[misc,assignment]
    socket.create_connection = refuse
    socket.getaddrinfo = refuse


def _limit_resources(memory_mb: int, cpu_seconds: int) -> None:
    try:
        import resource

        limit = memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 2))
    except (ImportError, ValueError, OSError):
        pass  # plataformas sem `resource` (Windows): fica só o limite de tempo


def _child(conn: Connection, target: str, args: tuple[Any, ...], memory_mb: int, cpu: int) -> None:
    try:
        _limit_resources(memory_mb, cpu)
        module_name, func_name = target.split(":")
        func = getattr(importlib.import_module(module_name), func_name)
        _block_network()
        conn.send(("ok", func(*args)))
    except BaseException as exc:
        conn.send(("err", f"{type(exc).__name__}: {exc}"))
    finally:
        conn.close()


def run_isolated(target: str, *args: Any, timeout: float = 60, memory_mb: int = 4096) -> Any:
    """Executa `modulo:funcao(*args)` em um subprocesso e devolve o resultado."""
    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_child, args=(child, target, args, memory_mb, int(timeout) + 5), daemon=True)
    proc.start()
    child.close()
    try:
        if not parent.poll(timeout):
            raise SandboxTimeout(f"O processamento excedeu {timeout:.0f}s e foi interrompido.")
        try:
            status, value = parent.recv()
        except EOFError as exc:
            raise SandboxError("O processo de importação terminou inesperadamente.") from exc
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join(5)
        parent.close()
    if status == "err":
        raise SandboxError(value)
    return value


def _parse(
    filename: str, data: bytes, assets: dict[str, bytes], importer: str
) -> tuple[str, dict[str, bytes]]:
    batch = get(importer).parse(Source(filename=filename, data=data, assets=assets))
    return batch.model_dump_json(), batch.assets


def parse_isolated(src: Source, importer: str, timeout: float = 120) -> ParsedBatch:
    sys.modules.setdefault("gotcha.importers", importlib.import_module("gotcha.importers"))
    payload, assets = run_isolated(
        "gotcha.sandbox:_parse", src.filename, src.data, src.assets, importer, timeout=timeout
    )
    batch = ParsedBatch.model_validate_json(payload)
    batch.assets = assets
    return batch
