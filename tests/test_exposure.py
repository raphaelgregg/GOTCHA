"""Em modo prova o gabarito não pode chegar à interface antes do fim."""

from gotcha.domain.exposure import public_view
from gotcha.domain.models import Choice, ImageRef, Question, QuestionKind


def question() -> Question:
    return Question(
        id="q1", number=1, kind=QuestionKind.SINGLE, stem="<p>x</p>",
        choices=[Choice(letter="A", text="a"), Choice(letter="B", text="b")],
        answer=["B"], explanation="porque sim",
        images=[ImageRef(name="e", sha="s1"), ImageRef(name="r", sha="s2", role="answer")],
        warnings=["interno"],
    )  # fmt: skip


def test_hidden_view_has_no_answer_explanation_or_answer_image() -> None:
    view = public_view(question(), reveal=False)
    assert "answer" not in view and "explanation" not in view
    assert [i["name"] for i in view["images"]] == ["e"]
    assert view["required_count"] == 1


def test_revealed_view_has_everything() -> None:
    view = public_view(question(), reveal=True)
    assert view["answer"] == ["B"] and view["explanation"] == "porque sim"
    assert {i["name"] for i in view["images"]} == {"e", "r"}


def test_multiple_exposes_required_count_but_not_letters() -> None:
    q = question().model_copy(update={"kind": QuestionKind.MULTIPLE, "answer": ["A", "B"]})
    view = public_view(q, reveal=False)
    assert view["required_count"] == 2 and "answer" not in view
