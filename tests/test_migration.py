"""Migração do modelo v1 (rascunhos e bancos existentes) para o modelo canônico v2."""

from gotcha.domain.models import Choice, ImageRef, QuestionKind
from gotcha.domain.models import Question as V1
from gotcha.qtypes import validate_question
from gotcha.qtypes.migrate import load_question, v1_to_v2

SHA = "b" * 64


def v1(**kw: object) -> V1:
    base: dict[str, object] = dict(
        number=3, topic=2, kind=QuestionKind.SINGLE, stem="<p>Qual?</p>",
        choices=[Choice(letter="A", text="um"), Choice(letter="B", text="dois")], answer=["B"],
    )  # fmt: skip
    return V1.model_validate({**base, **kw})


def test_single_becomes_multiple_choice_with_letter_ids() -> None:
    q = v1_to_v2(v1())
    assert q.type == "multiple_choice" and q.correct == "B"  # type: ignore[attr-defined]
    assert [o.id for o in q.options] == ["A", "B"]  # type: ignore[attr-defined]
    assert (q.topic, q.number) == (2, 3) and validate_question(q) == []


def test_multiple_and_true_false() -> None:
    m = v1_to_v2(v1(kind=QuestionKind.MULTIPLE, answer=["A", "B"]))
    assert m.type == "multiple_select" and m.correct == ["A", "B"]  # type: ignore[attr-defined]
    tf = v1_to_v2(
        v1(
            kind=QuestionKind.TRUE_FALSE,
            choices=[Choice(letter="A", text="Verdadeiro"), Choice(letter="B", text="Falso")],
        )
    )
    assert tf.type == "multiple_choice" and tf.variant == "true_false"  # type: ignore[attr-defined]


def test_interactive_becomes_self_assessed_keeping_images_in_place() -> None:
    q = v1_to_v2(
        v1(
            kind=QuestionKind.INTERACTIVE,
            choices=[],
            answer=[],
            explanation="nota",
            images=[
                ImageRef(name="e.png", sha=SHA),
                ImageRef(name="r.png", sha="c" * 64, role="answer"),
                ImageRef(name="falta.png"),
            ],
        )
    )
    assert q.type == "self_assessed"
    assets = [b for b in q.prompt if b.type == "image"]
    assert [a.asset for a in assets] == [
        SHA,
        None,
    ]  # imagem do enunciado e a ausente ficam no enunciado
    answer_assets = [b.asset for b in q.answer_blocks if b.type == "image"]  # type: ignore[attr-defined]
    assert answer_assets == ["c" * 64]
    assert q.conversion.status == "partial" and any("falta.png" in w for w in q.conversion.warnings)


def test_missing_answer_key_is_not_lost_it_becomes_self_assessed_with_a_warning() -> None:
    q = v1_to_v2(v1(answer=[]))
    assert q.type == "self_assessed" and q.conversion.status == "manual_required"
    text = " ".join(str(b) for b in q.prompt)
    assert "um" in text and "dois" in text  # alternativas preservadas no enunciado


def test_stem_html_becomes_html_block_and_warnings_are_carried() -> None:
    q = v1_to_v2(v1(warnings=["Algo estranho."]))
    assert q.prompt[0].type == "html" and "Qual?" in q.prompt[0].html
    assert "Algo estranho." in q.conversion.warnings


def test_load_question_reads_both_schema_versions() -> None:
    old = v1(id="abc123", exam_id="e1")
    assert load_question(old.model_dump_json()).type == "multiple_choice"
    new = v1_to_v2(old)
    assert load_question(new.model_dump_json()) == new


def test_v1_id_becomes_a_stable_uid() -> None:
    assert v1_to_v2(v1(id="abc123")).uid == v1_to_v2(v1(id="abc123")).uid == "q_abc123"
