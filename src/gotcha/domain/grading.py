"""Resultado de correção e resumo por grupo. A correção de cada tipo vive em `gotcha.qtypes`."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal


class Outcome(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"
    UNANSWERED = "unanswered"
    SELF_CORRECT = "self_correct"
    SELF_INCORRECT = "self_incorrect"


Group = Literal["auto", "self", "lab"]


@dataclass(frozen=True)
class Grade:
    score: float
    outcome: Outcome
    group: Group = "auto"
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Summary:
    """Pontuação separada por origem: automática, autoavaliada e laboratório simulado."""

    auto_total: int
    auto_correct: int
    auto_points: float
    self_total: int
    self_correct: int
    self_points: float
    lab_total: int
    lab_correct: int
    lab_points: float
    unanswered: int

    @property
    def auto_pct(self) -> float | None:
        return _pct(self.auto_points, self.auto_total)

    @property
    def self_pct(self) -> float | None:
        return _pct(self.self_points, self.self_total)

    @property
    def lab_pct(self) -> float | None:
        return _pct(self.lab_points, self.lab_total)


def _pct(points: float, total: int) -> float | None:
    return round(points / total * 100, 1) if total else None


def summarize(grades: Iterable[Grade]) -> Summary:
    items = list(grades)

    def part(group: Group) -> tuple[int, int, float]:
        mine = [g for g in items if g.group == group]  # em branco conta como 0 ponto
        full = sum(1 for g in mine if g.outcome in {Outcome.CORRECT, Outcome.SELF_CORRECT})
        return len(mine), full, sum(g.score for g in mine)

    a, s, lab = part("auto"), part("self"), part("lab")
    return Summary(
        auto_total=a[0], auto_correct=a[1], auto_points=a[2],
        self_total=s[0], self_correct=s[1], self_points=s[2],
        lab_total=lab[0], lab_correct=lab[1], lab_points=lab[2],
        unanswered=sum(1 for g in items if g.outcome is Outcome.UNANSWERED),
    )  # fmt: skip
