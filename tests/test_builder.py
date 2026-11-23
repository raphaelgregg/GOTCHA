"""Gerador de simulado: monta o exame a partir do banco, sem criar questões."""

from gotcha.domain.builder import History, SimuladoSpec, build
from gotcha.domain.grading import Outcome
from gotcha.qtypes.base import QuestionBase
from tests import qfactory as f


def make(n: int, topic: int = 1, kind: str = "multiple_choice", **kw: object) -> QuestionBase:
    return f.make(kind, uid=f"q{topic}-{n}", exam_id="e1", topic=topic, number=n, **kw)


BANK = [make(n, t) for t in (1, 2) for n in range(1, 11)]


def ids(questions: list[QuestionBase]) -> list[str]:
    return [x.uid for x in questions]


def test_same_seed_gives_same_order() -> None:
    spec = SimuladoSpec(exam_ids=["e1"], count=8, seed=42)
    assert ids(build(BANK, spec)) == ids(build(BANK, spec))


def test_different_seed_changes_order() -> None:
    a = build(BANK, SimuladoSpec(exam_ids=["e1"], seed=1))
    b = build(BANK, SimuladoSpec(exam_ids=["e1"], seed=2))
    assert ids(a) != ids(b)


def test_count_limits_questions_without_repeats() -> None:
    result = build(BANK, SimuladoSpec(exam_ids=["e1"], count=7, seed=3))
    assert len(result) == 7 and len(set(ids(result))) == 7


def test_count_larger_than_bank_returns_all() -> None:
    assert len(build(BANK, SimuladoSpec(exam_ids=["e1"], count=999, seed=1))) == 20


def test_filters_by_topic_and_exam() -> None:
    assert {x.topic for x in build(BANK, SimuladoSpec(exam_ids=["e1"], topics=[2], shuffle=False))} == {2}
    other = make(1).model_copy(update={"uid": "z", "exam_id": "e2"})
    assert ids(build([*BANK, other], SimuladoSpec(exam_ids=["e2"]))) == ["z"]


def test_without_shuffle_keeps_topic_and_number_order() -> None:
    result = build(BANK, SimuladoSpec(exam_ids=["e1"], shuffle=False))
    assert [(x.topic, x.number) for x in result] == sorted(x.position for x in BANK)


def test_can_exclude_interactive_types() -> None:
    bank = [
        make(1),
        make(2, kind="hot_area"),
        make(3, kind="self_assessed"),
        make(4, kind="multiple_select"),
    ]
    kept = build(bank, SimuladoSpec(exam_ids=["e1"], include_interactive=False, shuffle=False))
    assert [x.type for x in kept] == ["multiple_choice", "multiple_select"]


def test_history_filters() -> None:
    history = History(
        last_outcome={"q1-1": Outcome.INCORRECT, "q1-2": Outcome.PARTIAL, "q1-3": Outcome.CORRECT},
        marked={"q2-3"},
    )
    assert ids(build(BANK, SimuladoSpec(exam_ids=["e1"], only="wrong", shuffle=False), history)) == [
        "q1-1",
        "q1-2",
    ]
    assert ids(build(BANK, SimuladoSpec(exam_ids=["e1"], only="marked"), history)) == ["q2-3"]
    done = History(last_outcome={x.uid: Outcome.CORRECT for x in BANK[1:]})
    assert ids(build(BANK, SimuladoSpec(exam_ids=["e1"], only="unanswered"), done)) == ["q1-1"]


def test_case_study_questions_stay_together() -> None:
    bank = [make(1, case_id="c1"), make(2), make(3, case_id="c1"), make(4)]
    result = build(bank, SimuladoSpec(exam_ids=["e1"], seed=5))
    positions = [i for i, x in enumerate(result) if x.case_id == "c1"]
    assert positions == list(range(positions[0], positions[0] + 2))
