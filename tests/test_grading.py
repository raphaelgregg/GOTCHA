"""Corretores de questão: cada tipo de questão tem sua regra, registrada em um único lugar."""

import pytest

from gotcha.domain.grading import Outcome, Response, grade, summarize
from gotcha.domain.models import Choice, Question, QuestionKind


def q(kind: QuestionKind, answer: list[str], letters: str = "ABCD") -> Question:
    return Question(
        number=1,
        kind=kind,
        stem="Enunciado",
        choices=[Choice(letter=c, text=f"opção {c}") for c in letters],
        answer=answer,
    )


def test_single_choice_correct() -> None:
    assert grade(q(QuestionKind.SINGLE, ["B"]), Response(selected=["B"])) is Outcome.CORRECT


def test_single_choice_wrong() -> None:
    assert grade(q(QuestionKind.SINGLE, ["B"]), Response(selected=["C"])) is Outcome.INCORRECT


def test_unanswered_when_nothing_selected() -> None:
    assert grade(q(QuestionKind.SINGLE, ["B"]), Response()) is Outcome.UNANSWERED


def test_multiple_requires_exact_set() -> None:
    question = q(QuestionKind.MULTIPLE, ["A", "C"])
    assert grade(question, Response(selected=["C", "A"])) is Outcome.CORRECT
    assert grade(question, Response(selected=["A"])) is Outcome.INCORRECT
    assert grade(question, Response(selected=["A", "B", "C"])) is Outcome.INCORRECT


def test_true_false_behaves_like_single() -> None:
    question = q(QuestionKind.TRUE_FALSE, ["A"], letters="AB")
    assert grade(question, Response(selected=["A"])) is Outcome.CORRECT


def test_interactive_is_self_assessed() -> None:
    question = q(QuestionKind.INTERACTIVE, [], letters="")
    assert grade(question, Response()) is Outcome.UNANSWERED
    assert grade(question, Response(self_mark=True)) is Outcome.SELF_CORRECT
    assert grade(question, Response(self_mark=False)) is Outcome.SELF_INCORRECT


def test_interactive_ignores_selected_letters() -> None:
    question = q(QuestionKind.INTERACTIVE, [], letters="")
    assert grade(question, Response(selected=["A"])) is Outcome.UNANSWERED


def test_summary_separates_automatic_and_self_graded() -> None:
    outcomes = [
        Outcome.CORRECT,
        Outcome.INCORRECT,
        Outcome.CORRECT,
        Outcome.SELF_CORRECT,
        Outcome.SELF_INCORRECT,
        Outcome.UNANSWERED,
    ]
    result = summarize(outcomes)
    assert (result.auto_total, result.auto_correct) == (3, 2)
    assert result.auto_pct == pytest.approx(66.7, abs=0.1)
    assert (result.self_total, result.self_correct) == (2, 1)
    assert result.self_pct == 50.0
    assert result.unanswered == 1


def test_summary_without_self_graded_has_no_percentage() -> None:
    result = summarize([Outcome.CORRECT])
    assert result.self_pct is None
    assert result.auto_pct == 100.0


def test_summary_empty() -> None:
    result = summarize([])
    assert result.auto_pct is None and result.self_pct is None
