import pytest

from gotcha.domain.models import ParsedBatch, QuestionKind
from gotcha.importers.base import Source
from gotcha.importers.html_saved import HtmlImporter
from tests.html_fixture import card, page


def parse(html: bytes, assets: dict[str, bytes] | None = None) -> ParsedBatch:
    return HtmlImporter().parse(Source(filename="p.html", data=html, assets=assets or {}))


def test_detected_by_content() -> None:
    importer = HtmlImporter()
    assert importer.sniff(Source(filename="x.bin", data=page(card(1)))) > 0.5
    assert importer.sniff(Source(filename="x.html", data=b"<html><p>oi</p></html>")) < 0.5


def test_multiple_choice_card() -> None:
    html = page(card(7, topic=2, stem="Qual?", choices=["um", "dois", "tres"], answer="B"))
    q = parse(html).questions[0]
    assert (q.topic, q.number) == (2, 7)
    assert q.kind is QuestionKind.SINGLE and q.answer == ["B"]
    assert [c.text for c in q.choices] == ["um", "dois", "tres"]
    assert "Qual?" in q.stem


def test_multiple_answer_letters() -> None:
    html = page(card(1, choices=["a", "b", "c", "d"], answer="AC"))
    q = parse(html).questions[0]
    assert q.kind is QuestionKind.MULTIPLE and q.answer == ["A", "C"]


def test_interactive_card_with_missing_answer_image_is_flagged() -> None:
    html = page(card(3, stem="Arraste", answer_img="resp.png"))
    q = parse(html).questions[0]
    assert q.kind is QuestionKind.INTERACTIVE
    assert q.images[0].role == "answer" and q.images[0].missing
    assert any("anexo" in w.lower() for w in q.warnings)


def test_images_resolved_when_assets_present() -> None:
    html = page(card(3, stem="Arraste", answer_img="resp.png", stem_img="ex.png"))
    batch = parse(html, assets={"resp.png": b"PNG1", "ex.png": b"PNG2"})
    q = batch.questions[0]
    assert all(not img.missing for img in q.images)
    assert {img.role for img in q.images} == {"stem", "answer"}
    assert set(batch.assets.values()) == {b"PNG1", b"PNG2"}


def test_scripts_buttons_votes_and_discussion_are_not_in_stem() -> None:
    q = parse(page(card(1, stem="Texto limpo", choices=["a", "b"], answer="A"))).questions[0]
    for noise in ("Reveal", "Discussion", "50%", "var x"):
        assert noise not in q.stem


def test_most_voted_divergence_warns() -> None:
    html = page(card(1, choices=["a", "b", "c"], answer="A", voted="B"))
    q = parse(html).questions[0]
    assert q.answer == ["A"]
    assert any("votada" in w for w in q.warnings)


def test_page_without_questions_is_refused() -> None:
    with pytest.raises(ValueError, match="questões"):
        parse(b"<html><body><div class='exam-question-card-x'></div></body></html>")


def test_stem_html_is_sanitized() -> None:
    q = parse(page(card(1, stem="<b>ok</b><script>alert(1)</script>"))).questions[0]
    assert "<b>ok</b>" in q.stem and "script" not in q.stem
