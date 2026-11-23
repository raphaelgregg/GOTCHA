"""Gerador de simulado: seleciona e ordena questões já importadas (sem criar conteúdo)."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import groupby
from typing import Literal

from pydantic import BaseModel, Field

from .grading import Outcome
from .models import Question, QuestionKind


class SimuladoSpec(BaseModel):
    exam_ids: list[str]
    topics: list[int] | None = None
    count: int | None = Field(default=None, ge=1)
    shuffle: bool = True
    seed: int | None = None
    only: Literal["all", "wrong", "marked", "unanswered"] = "all"
    include_interactive: bool = True
    mode: Literal["study", "exam"] = "exam"
    time_limit_minutes: int | None = Field(default=None, ge=1)


@dataclass
class History:
    last_outcome: dict[str, Outcome] = field(default_factory=dict)
    marked: set[str] = field(default_factory=set)


_WRONG = {Outcome.INCORRECT, Outcome.SELF_INCORRECT}


def _eligible(q: Question, spec: SimuladoSpec, history: History) -> bool:
    qid = q.id or ""
    if q.exam_id not in spec.exam_ids:
        return False
    if spec.topics is not None and q.topic not in spec.topics:
        return False
    if not spec.include_interactive and q.kind is QuestionKind.INTERACTIVE:
        return False
    match spec.only:
        case "wrong":
            return history.last_outcome.get(qid) in _WRONG
        case "marked":
            return qid in history.marked
        case "unanswered":
            return qid not in history.last_outcome
        case _:
            return True


def _units(questions: Sequence[Question]) -> list[list[Question]]:
    """Agrupa questões do mesmo estudo de caso para que fiquem juntas."""
    units: list[list[Question]] = []
    by_case: dict[str, list[Question]] = {}
    for q in questions:
        if q.case_id is None:
            units.append([q])
        elif q.case_id in by_case:
            by_case[q.case_id].append(q)
        else:
            by_case[q.case_id] = [q]
            units.append(by_case[q.case_id])
    return units


def build(
    bank: Sequence[Question], spec: SimuladoSpec, history: History | None = None
) -> list[Question]:
    history = history or History()
    chosen = sorted(
        (q for q in bank if _eligible(q, spec, history)),
        key=lambda q: (q.exam_id or "", q.topic, q.number),
    )
    units = _units(chosen)
    if spec.shuffle:
        random.Random(spec.seed).shuffle(units)
    flat = [q for unit in units for q in unit]
    if spec.count is not None:
        flat = flat[: spec.count]
    return flat


def topics_of(bank: Sequence[Question]) -> list[int]:
    return [k for k, _ in groupby(sorted({q.topic for q in bank}))]
