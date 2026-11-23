from gotcha.domain.grading import Grade, Outcome, summarize


def g(score: float, outcome: Outcome, group: str = "auto") -> Grade:
    return Grade(score, outcome, group)  # type: ignore[arg-type]


def test_summary_separates_automatic_self_graded_and_lab() -> None:
    summary = summarize(
        [
            g(1, Outcome.CORRECT),
            g(0, Outcome.INCORRECT),
            g(1, Outcome.CORRECT),
            g(0.5, Outcome.PARTIAL),
            g(1, Outcome.SELF_CORRECT, "self"),
            g(0, Outcome.SELF_INCORRECT, "self"),
            g(1, Outcome.CORRECT, "lab"),
            g(0, Outcome.UNANSWERED),
        ]
    )
    assert (summary.auto_total, summary.auto_correct) == (5, 2)  # em branco conta como 0 ponto
    assert summary.auto_pct == 50.0  # (1 + 0 + 1 + 0.5 + 0) / 5
    assert (summary.self_total, summary.self_correct, summary.self_pct) == (2, 1, 50.0)
    assert (summary.lab_total, summary.lab_pct) == (1, 100.0)
    assert summary.unanswered == 1


def test_groups_without_questions_have_no_percentage() -> None:
    summary = summarize([g(1, Outcome.CORRECT)])
    assert summary.self_pct is None and summary.lab_pct is None and summary.auto_pct == 100.0
    assert summarize([]).auto_pct is None
