"""Contrato dos importadores e registro por detecção de conteúdo (nunca pela extensão)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from gotcha.domain.models import ParsedBatch


@dataclass
class Source:
    filename: str
    data: bytes
    # caminho relativo ou nome do arquivo -> bytes (imagens vindas de um ZIP)
    assets: dict[str, bytes] = field(default_factory=dict)


class UnsupportedFormat(ValueError):
    """Formato não reconhecido."""


class ProtectedFormat(UnsupportedFormat):
    """Formato fechado/protegido reconhecido: é recusado com orientação, nunca decodificado."""


class Importer(Protocol):
    name: str

    def sniff(self, src: Source) -> float:
        """Confiança de 0 a 1 de que o conteúdo é deste formato."""

    def parse(self, src: Source) -> ParsedBatch: ...


_REGISTRY: dict[str, Importer] = {}

# Assinaturas de formatos fechados: apenas reconhecer para orientar o usuário.
_PROTECTED: dict[bytes, str] = {
    bytes.fromhex("85a80304"): (
        "Arquivo VCE detectado. É um formato fechado e não é lido diretamente. "
        "Abra-o no aplicativo original e exporte o simulado para PDF; depois importe o PDF aqui."
    ),
}
MIN_CONFIDENCE = 0.5


def register(importer: Importer) -> Importer:
    _REGISTRY[importer.name] = importer
    return importer


def get(name: str) -> Importer:
    return _REGISTRY[name]


def names() -> list[str]:
    return sorted(_REGISTRY)


def detect(src: Source) -> Importer:
    for signature, guidance in _PROTECTED.items():
        if src.data.startswith(signature):
            raise ProtectedFormat(guidance)
    scored = sorted(((imp.sniff(src), imp) for imp in _REGISTRY.values()), key=lambda t: -t[0])
    best_score, best = scored[0]
    if best_score < MIN_CONFIDENCE:
        raise UnsupportedFormat(
            "Formato não reconhecido. Formatos aceitos: " + ", ".join(names()) + "."
        )
    return best
