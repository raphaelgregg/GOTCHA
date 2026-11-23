"""Valida os importadores com arquivos reais do usuário em samples/ (ignorada pelo git).

Ficam fora do CI: rodam só quando os arquivos existem. Cada falha real deve virar uma
fixture sintética em outro teste.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from gotcha.domain.models import QuestionKind
from gotcha.importers import Source, detect

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
pytestmark = pytest.mark.samples


def sample(pattern: str) -> Path:
    files = sorted(SAMPLES.glob(pattern))
    if not files:
        pytest.skip(f"sem amostra {pattern}")
    return files[0]


def load(path: Path):  # type: ignore[no-untyped-def]
    src = Source(filename=path.name, data=path.read_bytes())
    return detect(src).parse(src)


def test_html_page_has_fifty_questions_half_interactive() -> None:
    batch = load(sample("*Page_1*.html"))
    kinds = Counter(q.kind for q in batch.questions)
    assert len(batch.questions) == 50
    assert kinds[QuestionKind.INTERACTIVE] == 25
    assert all(q.answer for q in batch.questions if q.kind is not QuestionKind.INTERACTIVE)


def test_html_pages_overlap_is_keyed_by_topic_and_number() -> None:
    keys = [q.key for p in ("*Page_2*.html", "*Page_3*.html") for q in load(sample(p)).questions]
    assert len(keys) == 100 and len(set(keys)) == 100


def test_pdf_az140_extracts_all_questions_with_answers_and_no_leaks() -> None:
    batch = load(sample("*az-140.pdf"))
    assert [q.number for q in batch.questions] == list(range(1, 342))
    scored = [q for q in batch.questions if q.kind is not QuestionKind.INTERACTIVE]
    assert len(scored) == 216
    assert all(q.answer for q in scored), "questão pontuável sem gabarito"
    assert all(set(q.answer) <= {c.letter for c in q.choices} for q in scored)
    assert not [c for q in scored for c in q.choices if "correct answer" in c.text.lower()]


def test_txt_conversion_has_24_questions_and_one_shared_case() -> None:
    batch = load(sample("*PT-BR.txt"))
    assert len(batch.questions) == 24
    assert len(batch.cases) == 1
    assert sum(q.case_id is not None for q in batch.questions) == 3
