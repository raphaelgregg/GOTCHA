"""Correção de respostas. Cada tipo de questão registra seu corretor em um só lugar."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum

from .models import Question, QuestionKind


class Outcome(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNANSWERED = "unanswered"
    SELF_CORRECT = "self_correct"
    SELF_INCORRECT = "self_incorrect"


@dataclass(frozen=True)
class Response:
    selected: list[str] = field(default_factory=list)
    self_mark: bool | None = None


Grader = Callable[[Question, Response], Outcome]
GRADERS: dict[QuestionKind, Grader] = {}


def grader(*kinds: QuestionKind) -> Callable[[Grader], Grader]:
    def register(fn: Grader) -> Grader:
        for kind in kinds:
            GRADERS[kind] = fn
        return fn

    return register


@grader(QuestionKind.SINGLE, QuestionKind.TRUE_FALSE, QuestionKind.MULTIPLE)
def _by_letters(question: Question, response: Response) -> Outcome:
    if not response.selected:
        return Outcome.UNANSWERED
    same = set(response.selected) == set(question.answer)
    return Outcome.CORRECT if same else Outcome.INCORRECT


@grader(QuestionKind.INTERACTIVE)
def _self_assessed(_: Question, response: Response) -> Outcome:
    if response.self_mark is None:
        return Outcome.UNANSWERED
    return Outcome.SELF_CORRECT if response.self_mark else Outcome.SELF_INCORRECT


def grade(question: Question, response: Response) -> Outcome:
    return GRADERS[question.kind](question, response)


@dataclass(frozen=True)
class Summary:
    auto_total: int
    auto_correct: int
    self_total: int
    self_correct: int
    unanswered: int

    @property
    def auto_pct(self) -> float | None:
        return _pct(self.auto_correct, self.auto_total)

    @property
    def self_pct(self) -> float | None:
        return _pct(self.self_correct, self.self_total)


def _pct(part: int, total: int) -> float | None:
    return round(part / total * 100, 1) if total else None


def summarize(outcomes: Iterable[Outcome]) -> Summary:
    items = list(outcomes)
    count = items.count
    return Summary(
        auto_total=count(Outcome.CORRECT) + count(Outcome.INCORRECT),
        auto_correct=count(Outcome.CORRECT),
        self_total=count(Outcome.SELF_CORRECT) + count(Outcome.SELF_INCORRECT),
        self_correct=count(Outcome.SELF_CORRECT),
        unanswered=count(Outcome.UNANSWERED),
    )
