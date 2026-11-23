import io

import pytest
from openpyxl import Workbook

from gotcha.domain.models import QuestionKind
from gotcha.importers.base import Source
from gotcha.importers.json_app import JsonImporter, export_json
from gotcha.importers.tabular import CsvImporter, XlsxImporter

CSV = """numero,topico,pergunta,A,B,C,D,resposta,explicacao
1,1,Capital da Franca?,Paris,Roma,Lisboa,Madri,A,Fica no Sena
2,1,"Quais sao frutas?",Maca,Pedra,Banana,Ferro,"A,C",
"""


def test_csv_with_portuguese_headers() -> None:
    batch = CsvImporter().parse(Source(filename="a.csv", data=CSV.encode()))
    q1, q2 = batch.questions
    assert (
        q1.kind is QuestionKind.SINGLE and q1.answer == ["A"] and q1.explanation == "Fica no Sena"
    )
    assert q2.kind is QuestionKind.MULTIPLE and q2.answer == ["A", "C"]
    assert [c.text for c in q2.choices] == ["Maca", "Pedra", "Banana", "Ferro"]


def test_csv_semicolon_and_latin1() -> None:
    text = "number;question;A;B;answer\n1;Qual é a cor?;Azul;Verde;B\n"
    batch = CsvImporter().parse(Source(filename="a.csv", data=text.encode("latin-1")))
    assert batch.questions[0].stem.count("é") == 1


def test_csv_blank_choice_columns_are_dropped() -> None:
    text = "number,question,A,B,C,D,answer\n1,Q?,x,y,,,A\n"
    q = CsvImporter().parse(Source(filename="a.csv", data=text.encode())).questions[0]
    assert [c.letter for c in q.choices] == ["A", "B"]


def test_csv_missing_required_columns_is_refused() -> None:
    with pytest.raises(ValueError, match="colunas"):
        CsvImporter().parse(Source(filename="a.csv", data=b"foo,bar\n1,2\n"))


def test_csv_detected_by_content() -> None:
    assert CsvImporter().sniff(Source(filename="x.dat", data=CSV.encode())) > 0.5
    assert CsvImporter().sniff(Source(filename="x.csv", data=b"so uma linha")) < 0.5


def xlsx_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["number", "question", "A", "B", "answer"])
    ws.append([1, "Qual?", "um", "dois", "B"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_xlsx_same_rules_as_csv() -> None:
    src = Source(filename="a.xlsx", data=xlsx_bytes())
    assert XlsxImporter().sniff(src) > 0.9
    q = XlsxImporter().parse(src).questions[0]
    assert q.answer == ["B"] and q.choices[1].text == "dois"


def test_json_roundtrip() -> None:
    batch = CsvImporter().parse(Source(filename="a.csv", data=CSV.encode()))
    data = export_json(batch.title or "t", batch.questions, batch.cases)
    again = JsonImporter().parse(Source(filename="b.json", data=data))
    assert [q.model_dump(exclude={"id"}) for q in again.questions] == [
        q.model_dump(exclude={"id"}) for q in batch.questions
    ]


def test_json_requires_marker() -> None:
    assert JsonImporter().sniff(Source(filename="a.json", data=b'{"x": 1}')) < 0.5
    assert JsonImporter().sniff(Source(filename="a.json", data=b"[1,2")) < 0.5
