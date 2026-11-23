"""Importador de PDF com texto selecionável (sem OCR)."""

from __future__ import annotations

import re
from collections import Counter

import pypdfium2 as pdfium

from gotcha.domain.models import ParsedBatch

from .base import Source, register
from .text_blocks import BlockRules, parse_blocks

RULES = BlockRules(
    heading=re.compile(r"^(?:NEW\s+)?QUESTION\s*#?\s*(?P<n>\d+)\s*$", re.I),
    answer=re.compile(r"^(?:Correct\s+|Suggested\s+)?Answer\s*:[ \t]*(?P<a>.*)$", re.I),
)


def repeated_lines(pages: list[list[str]], min_pages: int = 3, ratio: float = 0.6) -> set[str]:
    """Cabeçalhos e rodapés: linhas que aparecem na maior parte das páginas."""
    if len(pages) < min_pages:
        return set()
    counts: Counter[str] = Counter()
    for lines in pages:
        counts.update(set(lines))
    return {ln for ln, n in counts.items() if n / len(pages) >= ratio}


class PdfImporter:
    name = "pdf"

    def sniff(self, src: Source) -> float:
        return 0.95 if src.data.startswith(b"%PDF") else 0.0

    def parse(self, src: Source) -> ParsedBatch:
        try:
            doc = pdfium.PdfDocument(src.data)
        except Exception as exc:  # senha, arquivo corrompido
            raise ValueError(f"Não foi possível abrir o PDF: {exc}") from exc
        pages = [
            [ln.strip() for ln in (doc[i].get_textpage().get_text_range() or "").splitlines()]
            for i in range(len(doc))
        ]
        if sum(len(" ".join(p).strip()) for p in pages) < 20 * max(1, len(pages)) // 2:
            raise ValueError(
                "O PDF não contém texto selecionável (pode ser digitalizado). "
                "OCR ainda não é suportado."
            )
        noise = repeated_lines(pages)
        lines = [ln for page in pages for ln in page if ln and ln not in noise]
        questions, cases, warnings = parse_blocks(lines, RULES)
        if not questions:
            raise ValueError("Nenhuma questão encontrada no PDF.")
        if any(q.kind.value == "interactive" for q in questions):
            warnings.append(
                "Imagens do PDF ainda não são extraídas; "
                "respostas em imagem ficam como anexo ausente."
            )
        return ParsedBatch(
            format=self.name,
            title=src.filename,
            questions=questions,
            cases=cases,
            warnings=warnings,
        )


register(PdfImporter())
