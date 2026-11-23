"""Entrada em ZIP (página + pasta de recursos) com limites contra zip bomb e path traversal."""

from __future__ import annotations

import io
import posixpath
import zipfile

from .base import Source

MAIN_EXTENSIONS = (".html", ".htm", ".txt", ".pdf", ".json", ".csv", ".xlsx")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")
MAX_TOTAL = 500 * 1024 * 1024
MAX_MEMBERS = 5000


class BundleError(ValueError):
    """Pacote ZIP inválido ou acima dos limites."""


def _safe(name: str) -> bool:
    norm = posixpath.normpath(name)
    return not (norm.startswith(("/", "..")) or ".." in norm.split("/") or "\\" in name)


def load_source(filename: str, data: bytes, max_total_bytes: int = MAX_TOTAL) -> Source:
    if not zipfile.is_zipfile(io.BytesIO(data)):
        return Source(filename=filename, data=data)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = [i for i in z.infolist() if not i.is_dir() and _safe(i.filename)]
        if "xl/workbook.xml" in z.namelist():
            return Source(filename=filename, data=data)  # é uma planilha, não um pacote
        if len(z.infolist()) > MAX_MEMBERS or sum(i.file_size for i in infos) > max_total_bytes:
            raise BundleError("O ZIP excede o limite de tamanho ou de quantidade de arquivos.")
        main = None
        for ext in MAIN_EXTENSIONS:
            candidates = [i for i in infos if i.filename.lower().endswith(ext)]
            if candidates:
                main = max(candidates, key=lambda i: i.file_size)
                break
        if main is None:
            raise BundleError("O ZIP não contém nenhum arquivo de simulado suportado.")
        assets: dict[str, bytes] = {}
        for info in infos:
            if info.filename.lower().endswith(IMAGE_EXTENSIONS):
                content = z.read(info)
                assets[posixpath.basename(info.filename)] = content
                assets[info.filename] = content
        return Source(filename=posixpath.basename(main.filename), data=z.read(main), assets=assets)
