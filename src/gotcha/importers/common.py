"""Funções compartilhadas pelos importadores."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Sequence
from html import escape

from gotcha.domain.models import Choice, QuestionKind

_TRUE_FALSE = {"true", "false", "verdadeiro", "falso", "yes", "no", "sim", "nao"}
_COMPACT = re.compile(r"[A-F]+")
_SEPARATED = re.compile(r"(?:[A-Fa-f][ ,;/+]+)+[A-Fa-f]")


def fold(text: str) -> str:
    """Minúsculas e sem acentos, para comparações tolerantes."""
    base = unicodedata.normalize("NFKD", text)
    return "".join(c for c in base if not unicodedata.combining(c)).lower()


def parse_letters(text: str) -> list[str]:
    """Extrai letras de resposta: 'B', 'AC', 'A, c'. Textos de marcador manual retornam []."""
    s = text.strip()
    if _COMPACT.fullmatch(s) or _SEPARATED.fullmatch(s):
        return sorted(set(re.findall(r"[A-F]", s.upper())))
    if len(s) == 1 and s.upper() in "ABCDEF":
        return [s.upper()]
    return []


def infer_kind(
    choices: Sequence[Choice], answer: Sequence[str], hint: QuestionKind | None = None
) -> QuestionKind:
    if hint is QuestionKind.INTERACTIVE or not choices:
        return QuestionKind.INTERACTIVE
    if len(answer) > 1:
        return QuestionKind.MULTIPLE
    if len(choices) == 2 and {fold(c.text).strip(" .") for c in choices} <= _TRUE_FALSE:
        return QuestionKind.TRUE_FALSE
    return QuestionKind.SINGLE


def plain_to_html(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "".join(f"<p>{escape(ln)}</p>" for ln in lines)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", errors="replace")


def validate_answer(choices: Sequence[Choice], answer: Sequence[str]) -> list[str]:
    """Avisos de consistência entre alternativas e gabarito."""
    warnings: list[str] = []
    letters = {c.letter for c in choices}
    if choices and not answer:
        warnings.append("Sem gabarito: defina a resposta correta na revisão.")
    elif not set(answer) <= letters:
        warnings.append("O gabarito cita alternativas que não existem.")
    return warnings
