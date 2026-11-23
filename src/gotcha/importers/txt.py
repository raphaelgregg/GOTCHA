"""Importador de TXT simples: `Q1`, enunciado, alternativas `A.`, `Answer: B`."""

from __future__ import annotations

import re

from gotcha.domain.models import ParsedBatch

from .base import Source, register
from .common import decode_text
from .text_blocks import BlockRules, parse_blocks

RULES = BlockRules(
    heading=re.compile(r"^Q(?P<n>\d+)$"),
    answer=re.compile(r"^Answer\s*:\s*(?P<a>.*)$", re.I),
)


class TxtImporter:
    name = "txt"

    def sniff(self, src: Source) -> float:
        text = decode_text(src.data[:200_000])
        headings = len(re.findall(r"(?m)^\s*Q\d+\s*$", text))
        answers = len(re.findall(r"(?mi)^\s*Answer\s*:", text))
        return 0.9 if headings >= 2 and answers >= 1 else 0.0

    def parse(self, src: Source) -> ParsedBatch:
        lines = decode_text(src.data).splitlines()
        questions, cases, warnings = parse_blocks(lines, RULES)
        if not questions:
            raise ValueError("Nenhuma questão encontrada no TXT.")
        return ParsedBatch(
            format=self.name,
            title=src.filename,
            questions=questions,
            cases=cases,
            warnings=warnings,
        )


register(TxtImporter())
