from gotcha.domain.models import Choice, QuestionKind
from gotcha.importers.common import infer_kind, parse_letters, plain_to_html


def ch(*texts: str) -> list[Choice]:
    return [Choice(letter="ABCDEF"[i], text=t) for i, t in enumerate(texts)]


def test_infer_single() -> None:
    assert infer_kind(ch("a", "b", "c"), ["A"]) is QuestionKind.SINGLE


def test_infer_multiple() -> None:
    assert infer_kind(ch("a", "b", "c"), ["A", "C"]) is QuestionKind.MULTIPLE


def test_infer_true_false() -> None:
    assert infer_kind(ch("True", "False"), ["A"]) is QuestionKind.TRUE_FALSE
    assert infer_kind(ch("Sim", "Não"), ["B"]) is QuestionKind.TRUE_FALSE


def test_infer_interactive_without_choices() -> None:
    assert infer_kind([], []) is QuestionKind.INTERACTIVE


def test_hint_interactive_wins() -> None:
    assert (
        infer_kind(ch("a", "b"), ["A"], hint=QuestionKind.INTERACTIVE) is QuestionKind.INTERACTIVE
    )


def test_parse_letters_variants() -> None:
    assert parse_letters("B") == ["B"]
    assert parse_letters("AC") == ["A", "C"]
    assert parse_letters("A, c") == ["A", "C"]
    assert parse_letters("B D") == ["B", "D"]
    assert parse_letters("[CONFIGURACAO MANUAL REQUERIDA]") == []
    assert parse_letters("") == []


def test_plain_to_html_escapes_and_keeps_lines() -> None:
    out = plain_to_html("a <b>\nc & d")
    assert "&lt;b&gt;" in out and "&amp;" in out and out.count("<p>") == 2
