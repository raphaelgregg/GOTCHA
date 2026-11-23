"""Formato JSON do próprio aplicativo (exportação e importação, também usado como backup)."""

from __future__ import annotations

import json
from collections.abc import Sequence

from gotcha.domain.models import CaseStudy, ParsedBatch, Question

from .base import Source, register

MARKER = "gotcha-json"


def export_json(title: str, questions: Sequence[Question], cases: Sequence[CaseStudy]) -> bytes:
    payload = {
        "format": MARKER,
        "version": 1,
        "title": title,
        "cases": [c.model_dump() for c in cases],
        "questions": [q.model_dump(mode="json") for q in questions],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


class JsonImporter:
    name = "json"

    def sniff(self, src: Source) -> float:
        head = src.data[:2000].lstrip()
        return 0.95 if head.startswith(b"{") and f'"{MARKER}"'.encode() in head else 0.0

    def parse(self, src: Source) -> ParsedBatch:
        try:
            data = json.loads(src.data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido: {exc}") from exc
        return ParsedBatch(
            format=self.name,
            title=str(data.get("title", src.filename)),
            questions=[Question.model_validate(q) for q in data.get("questions", [])],
            cases=[CaseStudy.model_validate(c) for c in data.get("cases", [])],
        )


register(JsonImporter())
