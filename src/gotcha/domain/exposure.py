"""O que a interface pode ver de uma questão. Em modo prova, nunca o gabarito antes do fim."""

from __future__ import annotations

from typing import Any

from .models import Question, QuestionKind


def public_view(q: Question, reveal: bool) -> dict[str, Any]:
    images = [i for i in q.images if reveal or i.role != "answer"]
    view: dict[str, Any] = {
        "id": q.id,
        "topic": q.topic,
        "number": q.number,
        "kind": q.kind.value,
        "stem": q.stem,
        "choices": [c.model_dump() for c in q.choices],
        "images": [{**i.model_dump(), "missing": i.missing} for i in images],
        "case_id": q.case_id,
    }
    if q.kind is not QuestionKind.INTERACTIVE:
        view["required_count"] = len(q.answer) if q.kind is QuestionKind.MULTIPLE else 1
    if reveal:
        view["answer"] = list(q.answer)
        view["explanation"] = q.explanation
    return view
