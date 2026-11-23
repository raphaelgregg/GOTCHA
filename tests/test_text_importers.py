"""TXT simples (Q1 / Answer:) e PDF compartilham o mesmo analisador de blocos."""

from gotcha.domain.models import ParsedBatch, QuestionKind
from gotcha.importers.base import Source
from gotcha.importers.pdf import PdfImporter
from gotcha.importers.txt import TxtImporter
from tests.pdfmaker import make_pdf

TXT = """Q1
AREA QUENTE (HOTSPOT) -
Voce tem um servidor.
Como configurar? Selecione na area de resposta.
[CONFIGURACAO MANUAL: Area_Quente]
Answer: [CONFIGURACAO MANUAL REQUERIDA]

Q2
Qual a cor do ceu?
A. Azul
B. Verde
C. Vermelho
Answer: A

Q3
Quais duas sao frutas?
A. Maca
B. Pedra
C. Banana
D. Ferro
Answer: AC

Q4
SIMULACAO
Configure o servidor.
[INSERIR IMAGEM MANUALMENTE: tabela_servidores]
[CONFIGURACAO MANUAL: Simulacao]
Answer: [CONFIGURACAO MANUAL REQUERIDA]

Q5
    Questao indentada?
    A. Sim
    B. Nao
    Answer: B
"""


def parse_txt(text: str = TXT) -> ParsedBatch:
    return TxtImporter().parse(Source(filename="x.txt", data=text.encode()))


def test_txt_detected_by_content_not_extension() -> None:
    importer = TxtImporter()
    assert importer.sniff(Source(filename="qualquer.bin", data=TXT.encode())) > 0.5
    assert importer.sniff(Source(filename="x.txt", data=b"apenas um texto qualquer")) < 0.5


def test_txt_counts_and_kinds() -> None:
    batch = parse_txt()
    kinds = {q.number: q.kind for q in batch.questions}
    assert kinds == {
        1: QuestionKind.INTERACTIVE,
        2: QuestionKind.SINGLE,
        3: QuestionKind.MULTIPLE,
        4: QuestionKind.INTERACTIVE,
        5: QuestionKind.TRUE_FALSE,
    }


def test_txt_choices_and_answers() -> None:
    q3 = next(q for q in parse_txt().questions if q.number == 3)
    assert [c.letter for c in q3.choices] == ["A", "B", "C", "D"]
    assert q3.choices[2].text == "Banana"
    assert q3.answer == ["A", "C"]


def test_txt_indented_blocks_are_read() -> None:
    q5 = next(q for q in parse_txt().questions if q.number == 5)
    assert q5.answer == ["B"] and len(q5.choices) == 2


def test_txt_placeholders_become_warnings_and_missing_images() -> None:
    q4 = next(q for q in parse_txt().questions if q.number == 4)
    assert q4.images and q4.images[0].missing and q4.images[0].name == "tabela_servidores"
    assert any("manual" in w.lower() for w in q4.warnings)
    assert "CONFIGURACAO" not in q4.stem and "INSERIR" not in q4.stem


def test_txt_stem_is_html_without_label_noise() -> None:
    q1 = parse_txt().questions[0]
    assert "<p>" in q1.stem and "Voce tem um servidor." in q1.stem


CASE = """Q1
Estudo de Caso -
Este e um estudo de caso.
Visao Geral -
A empresa X tem dois escritorios.
Requisitos -
Migrar tudo para a nuvem.
Qual servico usar?
A. Alfa
B. Beta
Answer: B

Q2
Estudo de Caso -
Este e um estudo de caso.
Visao Geral -
A empresa X tem dois escritorios.
Requisitos -
Migrar tudo para a nuvem.
Qual regiao escolher?
A. Norte
B. Sul
Answer: A

Q3
Pergunta solta?
A. Um
B. Dois
Answer: A
"""


def test_case_study_context_is_shared_once() -> None:
    batch = parse_txt(CASE)
    assert len(batch.cases) == 1
    assert "dois escritorios" in batch.cases[0].text
    q1, q2, q3 = batch.questions
    assert q1.case_id == q2.case_id == batch.cases[0].id
    assert q3.case_id is None
    assert "dois escritorios" not in q1.stem and "Qual servico usar?" in q1.stem
    assert "Qual regiao escolher?" in q2.stem


def make_pdf_text() -> bytes:
    page1 = [
        "Microsoft - XX-100 Practice Questions",
        "Question #1",
        "Qual e a capital da Franca?",
        "A) Paris",
        "B) Roma",
        "C) Lisboa",
        "Explanation",
        "Correct Answer: A",
        "Reference:",
        "https://example.test/ref",
        "Community Discussion",
        "alguem comentou: a resposta B esta certa",
        "Page 1 of 3",
    ]
    page2 = [
        "Microsoft - XX-100 Practice Questions",
        "Question #2",
        "HOTSPOT -",
        "Selecione as opcoes na area de resposta.",
        "Hot Area:",
        "Explanation",
        "Correct Answer:",
        "Community Discussion",
        "Page 2 of 3",
    ]
    page3 = [
        "Microsoft - XX-100 Practice Questions",
        "Question #3",
        "Quais duas opcoes?",
        "A. isto faz parte do enunciado",
        "A) Um",
        "B) Dois",
        "C) Tres",
        "Explanation",
        "Correct Answer: AB",
        "Page 3 of 3",
    ]
    return make_pdf([page1, page2, page3])


def parse_pdf() -> ParsedBatch:
    return PdfImporter().parse(Source(filename="a.pdf", data=make_pdf_text()))


def test_pdf_detected_by_magic() -> None:
    assert PdfImporter().sniff(Source(filename="x", data=make_pdf_text())) > 0.9
    assert PdfImporter().sniff(Source(filename="x.pdf", data=b"nao e pdf")) < 0.5


def test_pdf_segments_questions() -> None:
    batch = parse_pdf()
    assert [q.number for q in batch.questions] == [1, 2, 3]
    q1, q2, q3 = batch.questions
    assert q1.kind is QuestionKind.SINGLE and q1.answer == ["A"]
    assert [c.text for c in q1.choices] == ["Paris", "Roma", "Lisboa"]
    assert q2.kind is QuestionKind.INTERACTIVE and q2.choices == []
    assert q3.kind is QuestionKind.MULTIPLE and q3.answer == ["A", "B"]


def test_pdf_discards_headers_footers_and_community_comments() -> None:
    batch = parse_pdf()
    everything = " ".join(q.stem + " ".join(c.text for c in q.choices) for q in batch.questions)
    assert "Practice Questions" not in everything
    assert "Page 1 of 3" not in everything
    assert "alguem comentou" not in everything


def test_pdf_stem_line_starting_with_option_letter_is_not_an_option() -> None:
    q3 = parse_pdf().questions[2]
    assert [c.letter for c in q3.choices] == ["A", "B", "C"]
    assert q3.choices[0].text == "Um"
    assert "faz parte do enunciado" in q3.stem


def test_pdf_without_text_is_refused_with_guidance() -> None:
    import pytest

    empty = make_pdf([[""], [""]])
    with pytest.raises(ValueError, match=r"OCR|texto"):
        PdfImporter().parse(Source(filename="a.pdf", data=empty))
