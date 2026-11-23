"""Funções de nível de módulo executadas dentro do subprocesso nos testes do sandbox."""

import socket
import time


def double(x: int) -> int:
    return x * 2


def sleeper(seconds: float) -> str:
    time.sleep(seconds)
    return "acordei"


def try_network() -> str:
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    except OSError as exc:
        return f"bloqueado: {type(exc).__name__}"
    return "conectou"


def boom() -> None:
    raise RuntimeError("falha interna")
