"""Importador de PDF com texto selecionável (sem OCR)."""

from __future__ import annotations

import re
from collections import Counter

import pypdfium2 as pdfium

from gotcha.domain.models import ImageRef, ParsedBatch

from .base import Source, register
from .pdf_images import associate, read_images, read_markers, split_decorative
from .text_blocks import BlockRules, parse_blocks

RULES = BlockRules(
    heading=re.compile(r"^(?:NEW\s+)?QUESTION\s*#?\s*(?P<n>\d+)\s*$", re.I),
    answer=re.compile(r"^(?:Correct\s+|Suggested\s+)?Answer\s*:[ \t]*(?P<a>.*)$", re.I),
)


_DIGITS = re.compile(r"\d+")
_SECTION = re.compile(r"^(explanation|reference|community discussion)", re.I)


def _structural(line: str) -> bool:
    """Linhas que delimitam questões nunca são tratadas como cabeçalho ou rodapé."""
    return bool(RULES.heading.match(line) or RULES.answer.match(line) or _SECTION.match(line))


def _shape(line: str) -> str:
    """Linha sem números, para reconhecer cabeçalhos como '14 Curso X' e '15 Curso X'."""
    return _DIGITS.sub("#", line)


def repeated_lines(pages: list[list[str]], min_pages: int = 3, ratio: float = 0.8) -> set[str]:
    """Formas de linha (sem números) que aparecem na maior parte das páginas: cabeçalho/rodapé."""
    if len(pages) < min_pages:
        return set()
    counts: Counter[str] = Counter()
    for lines in pages:
        counts.update({_shape(ln) for ln in lines if ln and not _structural(ln)})
    return {shape for shape, n in counts.items() if n / len(pages) >= ratio}


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
                "O PDF não contém texto selecionável (pode ser digitalizado). OCR ainda não é suportado."
            )
        noise = repeated_lines(pages)
        lines = [ln for page in pages for ln in page if ln and (_structural(ln) or _shape(ln) not in noise)]
        questions, cases, warnings = parse_blocks(lines, RULES)
        if not questions:
            raise ValueError("Nenhuma questão encontrada no PDF.")
        assets: dict[str, bytes] = {}
        warnings += self._attach_images(doc, questions, assets)
        return ParsedBatch(
            format=self.name,
            title=src.filename,
            questions=questions,
            cases=cases,
            warnings=warnings,
            assets=assets,
        )

    @staticmethod
    def _attach_images(doc: pdfium.PdfDocument, questions: list, assets: dict[str, bytes]) -> list[str]:  # type: ignore[type-arg]
        images, failed = read_images(doc)
        kept, decorative = split_decorative(images, len(doc))
        found = associate(read_markers(doc, RULES.heading, RULES.answer), kept)
        by_number = {q.number: q for q in questions}
        warnings: list[str] = []
        for number, role, img in found.placed:
            q = by_number.get(number)
            if q is None:
                found.orphans.append(img)
                continue
            assets[img.sha] = img.png
            q.images.append(ImageRef(name=img.name, sha=img.sha, role=role))  # type: ignore[arg-type]
        if found.orphans:
            pages = sorted({i.page + 1 for i in found.orphans})
            warnings.append(
                f"{len(found.orphans)} imagem(ns) sem questão associada "
                f"(páginas {', '.join(map(str, pages[:10]))})."
            )
        if decorative:
            warnings.append(
                f"{decorative} imagem(ns) decorativa(s) repetida(s) em várias páginas foram ignoradas."
            )
        if failed:
            warnings.append(f"{failed} imagem(ns) do PDF não puderam ser extraídas.")
        return warnings


register(PdfImporter())
