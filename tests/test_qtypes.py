"""Suíte de contrato: todo tipo de questão passa pelas mesmas verificações."""

from __future__ import annotations

import json
from typing import Any

import pytest

from gotcha.domain.grading import Outcome
from gotcha.qtypes import REGISTRY, grade_question, parse_question, public_view, validate_question
from tests import qfactory as f


def keys_of(value: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            out.add(k)
            out |= keys_of(v)
    elif isinstance(value, list):
        for v in value:
            out |= keys_of(v)
    return out


def test_every_type_in_the_requirement_is_registered() -> None:
    required = {
        "multiple_choice",
        "multiple_select",
        "drag_drop",
        "build_list",
        "hot_area",
        "active_screen",
        "lab",
    }
    assert required <= set(REGISTRY)
    assert "self_assessed" in REGISTRY


@pytest.mark.parametrize("name", f.ALL)
def test_serialization_roundtrip(name: str) -> None:
    q = f.make(name)
    again = parse_question(json.loads(q.model_dump_json()))
    assert again == q


@pytest.mark.parametrize("name", f.ALL)
def test_valid_sample_has_no_semantic_errors(name: str) -> None:
    assert validate_question(f.make(name)) == []


@pytest.mark.parametrize("name", f.ALL)
def test_semantic_validator_catches_broken_questions(name: str) -> None:
    q = f.make(name)
    broken = q.model_copy(update=f.BROKEN[name])
    assert validate_question(broken), f"validador não percebeu a quebra em {name}"


@pytest.mark.parametrize("name", f.ALL)
def test_exam_view_never_contains_the_answer_key(name: str) -> None:
    view = public_view(f.make(name), reveal=False, seed=1)
    leaked = keys_of(view) & f.HIDDEN[name]
    assert not leaked, f"{name} vazou {leaked}"
    assert "explanation" not in view


@pytest.mark.parametrize("name", [n for n in f.ALL if n != "lab_external"])
def test_revealed_view_contains_the_key(name: str) -> None:
    view = public_view(f.make(name), reveal=True, seed=1)
    assert view.get("key"), f"{name} não revelou o gabarito"


@pytest.mark.parametrize("name", f.ALL)
def test_correct_response_scores_full_and_wrong_does_not(name: str) -> None:
    q = f.make(name)
    right = grade_question(q, f.CORRECT[name])
    wrong = grade_question(q, f.WRONG[name])
    assert right.score == 1.0
    assert right.outcome in {Outcome.CORRECT, Outcome.SELF_CORRECT}
    assert wrong.score < 1.0
    assert wrong.outcome in {Outcome.INCORRECT, Outcome.SELF_INCORRECT, Outcome.PARTIAL}


@pytest.mark.parametrize("name", f.ALL)
def test_empty_response_is_unanswered(name: str) -> None:
    assert grade_question(f.make(name), None).outcome is Outcome.UNANSWERED


@pytest.mark.parametrize("name", f.ALL)
def test_malformed_response_is_rejected(name: str) -> None:
    with pytest.raises(ValueError):
        grade_question(f.make(name), {"campo_inexistente": 1})


def test_fingerprint_ignores_identity_and_position() -> None:
    a = f.make("multiple_choice")
    b = f.make("multiple_choice", uid="outro", number=99, topic=7)
    assert a.fingerprint() == b.fingerprint()
    c = f.make("multiple_choice", correct="a")
    assert a.fingerprint() != c.fingerprint()


def test_group_of_each_type() -> None:
    assert grade_question(f.make("lab_simulated"), f.CORRECT["lab_simulated"]).group == "lab"
    assert grade_question(f.make("lab_external"), f.CORRECT["lab_external"]).group == "self"
    assert grade_question(f.make("self_assessed"), f.CORRECT["self_assessed"]).group == "self"
    assert grade_question(f.make("hot_area"), f.CORRECT["hot_area"]).group == "auto"


def test_partial_credit_when_enabled() -> None:
    q = f.make("multiple_select", scoring={"points": 1, "partial": True})
    g = grade_question(q, {"selected": ["a"]})
    assert g.outcome is Outcome.PARTIAL and g.score == pytest.approx(0.5)
    assert grade_question(q, {"selected": ["a", "d"]}).score == 0.0  # um acerto menos um erro
    seq = f.make("build_list", scoring={"points": 1, "partial": True})
    assert grade_question(seq, {"sequence": ["p3", "p2", "p1"]}).score == pytest.approx(1 / 3)
    dd = f.make("drag_drop", scoring={"points": 1, "partial": True})
    assert grade_question(dd, {"placements": {"t1": ["i1"], "t2": ["i1"]}}).score == pytest.approx(0.5)


def test_hot_area_multiple_selection_and_required_count() -> None:
    q = f.make("hot_area", correct=["s1", "s3"], selection={"mode": "multiple", "required_count": 2})
    assert grade_question(q, {"selected": ["s3", "s1"]}).score == 1.0
    assert grade_question(q, {"selected": ["s1"]}).score < 1.0


def test_build_list_pool_is_shuffled_deterministically_and_keeps_decoys() -> None:
    q = f.make("build_list")
    a = public_view(q, reveal=False, seed=7)["pool"]
    b = public_view(q, reveal=False, seed=7)["pool"]
    c = public_view(q, reveal=False, seed=8)["pool"]
    assert a == b and {p["id"] for p in a} == {"p1", "p2", "p3", "p4"}
    assert [p["id"] for p in a] != [p["id"] for p in c]
