"""Gerador de simulado: monta o exame a partir do banco, sem criar questões."""

from gotcha.domain.builder import History, SimuladoSpec, build
from gotcha.domain.grading import Outcome
from gotcha.domain.models import Choice, Question, QuestionKind


def make(n: int, topic: int = 1, kind: QuestionKind = QuestionKind.SINGLE) -> Question:
    return Question(
        id=f"q{topic}-{n}",
        exam_id="e1",
        topic=topic,
        number=n,
        kind=kind,
        stem="x",
        choices=[Choice(letter="A", text="a"), Choice(letter="B", text="b")],
        answer=["A"],
    )


BANK = [make(n, t) for t in (1, 2) for n in range(1, 11)]


def ids(questions: list[Question]) -> list[str]:
    return [x.id or "" for x in questions]


def test_same_seed_gives_same_order() -> None:
    spec = SimuladoSpec(exam_ids=["e1"], count=8, seed=42)
    assert ids(build(BANK, spec)) == ids(build(BANK, spec))


def test_different_seed_changes_order() -> None:
    a = build(BANK, SimuladoSpec(exam_ids=["e1"], seed=1))
    b = build(BANK, SimuladoSpec(exam_ids=["e1"], seed=2))
    assert ids(a) != ids(b)


def test_count_limits_questions_without_repeats() -> None:
    result = build(BANK, SimuladoSpec(exam_ids=["e1"], count=7, seed=3))
    assert len(result) == 7
    assert len(set(ids(result))) == 7


def test_count_larger_than_bank_returns_all() -> None:
    assert len(build(BANK, SimuladoSpec(exam_ids=["e1"], count=999, seed=1))) == 20


def test_filters_by_topic() -> None:
    result = build(BANK, SimuladoSpec(exam_ids=["e1"], topics=[2], shuffle=False))
    assert {x.topic for x in result} == {2}


def test_without_shuffle_keeps_topic_and_number_order() -> None:
    result = build(BANK, SimuladoSpec(exam_ids=["e1"], shuffle=False))
    assert [(x.topic, x.number) for x in result] == sorted((x.topic, x.number) for x in BANK)


def test_filters_by_exam() -> None:
    other = make(1).model_copy(update={"id": "z", "exam_id": "e2"})
    result = build([*BANK, other], SimuladoSpec(exam_ids=["e2"]))
    assert ids(result) == ["z"]


def test_can_exclude_interactive() -> None:
    bank = [make(1), make(2, kind=QuestionKind.INTERACTIVE)]
    result = build(bank, SimuladoSpec(exam_ids=["e1"], include_interactive=False))
    assert [x.kind for x in result] == [QuestionKind.SINGLE]


def test_only_wrong_uses_history() -> None:
    history = History(
        last_outcome={"q1-1": Outcome.INCORRECT, "q1-2": Outcome.CORRECT},
    )
    result = build(BANK, SimuladoSpec(exam_ids=["e1"], only="wrong"), history)
    assert ids(result) == ["q1-1"]


def test_only_marked_uses_history() -> None:
    history = History(marked={"q2-3"})
    result = build(BANK, SimuladoSpec(exam_ids=["e1"], only="marked"), history)
    assert ids(result) == ["q2-3"]


def test_only_unanswered_means_never_attempted() -> None:
    history = History(last_outcome={x.id or "": Outcome.CORRECT for x in BANK[1:]})
    result = build(BANK, SimuladoSpec(exam_ids=["e1"], only="unanswered"), history)
    assert ids(result) == ["q1-1"]


def test_case_study_questions_stay_together() -> None:
    bank = [
        make(1).model_copy(update={"case_id": "c1"}),
        make(2),
        make(3).model_copy(update={"case_id": "c1"}),
        make(4),
    ]
    result = build(bank, SimuladoSpec(exam_ids=["e1"], seed=5))
    positions = [i for i, x in enumerate(result) if x.case_id == "c1"]
    assert positions == list(range(positions[0], positions[0] + 2))
