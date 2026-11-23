"""Importadores de CSV e XLSX: mesmas regras, com cabeçalhos em português ou inglês."""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Sequence

from openpyxl import load_workbook

from gotcha.domain.models import Choice, ParsedBatch, Question
from gotcha.domain.sanitize import clean_html

from .base import Source, register
from .common import decode_text, fold, infer_kind, parse_letters, plain_to_html, validate_answer

_ALIASES = {
    "number": {"number", "numero", "num", "n", "#", "questao", "question number"},
    "topic": {"topic", "topico", "tema", "assunto"},
    "stem": {"question", "pergunta", "enunciado", "stem", "texto", "questao texto"},
    "answer": {"answer", "resposta", "gabarito", "correct", "correta", "correct answer"},
    "explanation": {"explanation", "explicacao", "comentario", "justificativa"},
}
_CHOICE_PREFIXES = ("", "opcao ", "alternativa ", "choice ", "option ", "resposta ")


def _column_roles(header: Sequence[str]) -> dict[int, str]:
    roles: dict[int, str] = {}
    for i, raw in enumerate(header):
        h = fold(raw).strip()
        for role, names in _ALIASES.items():
            if h in names and role not in roles.values():
                roles[i] = role
                break
        else:
            for letter in "abcdef":
                if any(h == p + letter for p in _CHOICE_PREFIXES):
                    roles[i] = f"choice:{letter.upper()}"
                    break
    return roles


def cell(row: list[str], by_role: dict[str, int], role: str) -> str:
    index = by_role.get(role)
    return row[index].strip() if index is not None and index < len(row) else ""


def rows_to_batch(name: str, rows: list[list[str]], fmt: str) -> ParsedBatch:
    if not rows:
        raise ValueError("Planilha vazia.")
    roles = _column_roles(rows[0])
    if "stem" not in roles.values():
        raise ValueError(
            "Não encontrei as colunas obrigatórias. É preciso ao menos uma coluna de pergunta "
            "(question/pergunta/enunciado) e as alternativas A, B, C…"
        )
    by_role = {role: i for i, role in roles.items()}
    questions: list[Question] = []
    for n, row in enumerate(rows[1:], start=1):
        stem = cell(row, by_role, "stem")
        if not stem:
            continue
        choices = [
            Choice(letter=role[7:], text=cell(row, by_role, role))
            for role in sorted(r for r in by_role if r.startswith("choice:"))
            if cell(row, by_role, role)
        ]
        answer = parse_letters(cell(row, by_role, "answer"))
        number_text = cell(row, by_role, "number")
        topic_text = cell(row, by_role, "topic")
        q = Question(
            number=int(float(number_text)) if number_text.replace(".", "", 1).isdigit() else n,
            topic=int(float(topic_text)) if topic_text.replace(".", "", 1).isdigit() else 1,
            kind=infer_kind(choices, answer),
            stem=clean_html(stem) if "<" in stem else plain_to_html(stem),
            choices=choices,
            answer=answer,
            explanation=cell(row, by_role, "explanation"),
        )
        q.warnings = validate_answer(choices, answer) if q.kind.value != "interactive" else []
        questions.append(q)
    if not questions:
        raise ValueError("Nenhuma questão encontrada na planilha.")
    return ParsedBatch(format=fmt, title=name, questions=questions)


class CsvImporter:
    name = "csv"

    def sniff(self, src: Source) -> float:
        head = decode_text(src.data[:4096]).splitlines()
        if len(head) < 2:
            return 0.0
        for delim in (",", ";", "\t"):
            cols = [c for c in next(csv.reader([head[0]], delimiter=delim), [])]
            if len(cols) >= 3 and "stem" in _column_roles(cols).values():
                return 0.8
        return 0.0

    def parse(self, src: Source) -> ParsedBatch:
        text = decode_text(src.data)
        try:
            delim = csv.Sniffer().sniff(text[:2048], delimiters=",;\t").delimiter
        except csv.Error:
            delim = ","
        try:
            rows = [list(r) for r in csv.reader(io.StringIO(text), delimiter=delim)]
        except csv.Error as exc:
            raise ValueError(f"CSV inválido: {exc}") from exc
        return rows_to_batch(src.filename, rows, self.name)


class XlsxImporter:
    name = "xlsx"

    def sniff(self, src: Source) -> float:
        if not src.data.startswith(b"PK"):
            return 0.0
        try:
            with zipfile.ZipFile(io.BytesIO(src.data)) as z:
                return 0.95 if "xl/workbook.xml" in z.namelist() else 0.0
        except zipfile.BadZipFile:
            return 0.0

    def parse(self, src: Source) -> ParsedBatch:
        wb = load_workbook(io.BytesIO(src.data), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        rows = [["" if c is None else str(c) for c in row] for row in ws.iter_rows(values_only=True)]
        return rows_to_batch(src.filename, rows, self.name)


register(CsvImporter())
register(XlsxImporter())
