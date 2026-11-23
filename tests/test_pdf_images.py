"""Imagens do PDF: extraídas com posição e ligadas à questão certa, sem descartar nada em silêncio."""

from collections.abc import Mapping, Sequence

from gotcha.domain.models import ParsedBatch, QuestionKind
from gotcha.importers.base import Source
from gotcha.importers.pdf import PdfImporter
from gotcha.importers.pdf_images import PageImage, associate
from gotcha.qtypes.assets import analyze
from gotcha.qtypes.migrate import v1_to_v2
from tests.pdfmaker import Image, make_pdf

RED, GREEN, BLUE, GRAY = (255, 0, 0), (0, 255, 0), (0, 0, 255), (90, 90, 90)
# Linhas a cada 12 pt a partir de y=800: o "topo" de cada linha fica ~7 pt acima da linha de base.
HOTSPOT = [
    "Question #1", "HOTSPOT -", "Selecione na area de resposta.", "Hot Area:",  # y 800, 788, 776, 764
    "Explanation", "Correct Answer:", "Reference:", "Community Discussion",  # y 752, 740, 728, 716
]  # fmt: skip
CHOICE = ["Question #2", "Qual?", "A) um", "B) dois", "Explanation", "Correct Answer:", "B"]


def parse(pages: list[list[str]], images: Mapping[int, Sequence[Image]]) -> ParsedBatch:
    return PdfImporter().parse(Source(filename="a.pdf", data=make_pdf(pages, images)))


def test_image_before_explanation_is_the_stem_and_after_the_answer_label_is_the_answer() -> None:
    images = {0: [(60, 768, 100, 10, RED), (60, 742, 100, 10, GREEN)]}  # topos em 778 e 752
    q = parse([HOTSPOT, CHOICE, CHOICE], images).questions[0]
    roles = {i.role: i for i in q.images}
    assert set(roles) == {"stem", "answer"}
    assert roles["stem"].sha != roles["answer"].sha and not any(i.missing for i in q.images)


def test_interactive_question_with_answer_image_keeps_it_as_the_reference_answer() -> None:
    images = {0: [(60, 742, 100, 10, GREEN)]}
    batch = parse([HOTSPOT, CHOICE, CHOICE], images)
    q = batch.questions[0]
    assert q.kind is QuestionKind.INTERACTIVE
    v2 = v1_to_v2(q)
    assert v2.type == "self_assessed"
    answer_assets = [b.asset for b in v2.answer_blocks if b.type == "image"]  # type: ignore[attr-defined]
    assert answer_assets == [q.images[0].sha] and answer_assets[0] in batch.assets


def test_extracted_images_are_lossless_valid_pngs() -> None:
    images = {0: [(60, 742, 100, 10, GREEN)]}
    batch = parse([HOTSPOT, CHOICE, CHOICE], images)
    ((sha, data),) = batch.assets.items()
    info = analyze(data)
    assert info.mime == "image/png" and info.sha == sha


def test_image_at_the_top_of_the_next_page_belongs_to_the_previous_question() -> None:
    page2 = [
        "Continuacao do enunciado",
        "Question #2",
        "Qual?",
        "A) um",
        "B) dois",
        "Explanation",
        "Correct Answer:",
        "B",
    ]
    images = {1: [(60, 805, 100, 10, BLUE)]}  # acima da primeira linha da página 2
    batch = parse([[*HOTSPOT[:4], "A) a"], page2, CHOICE], images)
    assert [i.role for i in batch.questions[0].images] == ["stem"]
    assert batch.questions[1].images == []


def test_image_before_any_question_is_reported_not_dropped() -> None:
    page1 = ["Capa do documento", *CHOICE]
    images = {0: [(60, 805, 100, 10, RED)]}
    batch = parse([page1, CHOICE, CHOICE], images)
    assert any("sem questão" in w for w in batch.warnings)


def test_decorative_image_repeated_on_every_page_is_filtered_and_counted() -> None:
    pages = [CHOICE, CHOICE, CHOICE, CHOICE]
    images = {i: [(500, 30, 40, 40, GRAY)] for i in range(4)}
    batch = parse(pages, images)
    assert all(q.images == [] for q in batch.questions) and batch.assets == {}
    assert any("decorativ" in w for w in batch.warnings)


def test_same_image_used_by_two_questions_is_stored_once() -> None:
    page1 = [*CHOICE, "Question #3", "Qual?", "A) x", "B) y", "Explanation", "Correct Answer:", "A"]
    images = {0: [(60, 740, 40, 8, RED), (60, 690, 40, 8, RED)]}
    batch = parse([page1, CHOICE, CHOICE], images)
    shas = {i.sha for q in batch.questions for i in q.images}
    assert len(batch.assets) == 1 and len(shas) == 1


def test_associate_is_a_pure_reading_order_function() -> None:
    from gotcha.importers.pdf_images import Marker

    events = [
        Marker(page=0, y=800, kind="heading", number=1),
        Marker(page=0, y=700, kind="explanation"),
        Marker(page=0, y=600, kind="answer"),
        Marker(page=1, y=800, kind="heading", number=2),
    ]
    imgs = [
        PageImage(page=0, y=750, png=b"a", name="a"),
        PageImage(page=0, y=550, png=b"b", name="b"),
        PageImage(page=1, y=790, png=b"c", name="c"),
    ]
    result = associate(events, imgs)
    assert [(q, r) for q, r, _ in result.placed] == [(1, "stem"), (1, "answer"), (2, "stem")]
    assert result.orphans == []
