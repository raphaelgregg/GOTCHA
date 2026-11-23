import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gotcha.api.app import create_app
from tests import imgs
from tests.html_fixture import card, page

TXT = b"""Q1
Qual a cor do ceu?
A. Azul
B. Verde
Answer: A

Q2
Quais duas sao frutas?
A. Maca
B. Pedra
C. Banana
Answer: AC

Q3
SIMULACAO
Configure o servidor.
[CONFIGURACAO MANUAL: Simulacao]
Answer: [CONFIGURACAO MANUAL REQUERIDA]
"""


class FakeClock:
    def __init__(self) -> None:
        self.t = 5000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture()
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture()
def client(tmp_path: Path, clock: FakeClock) -> TestClient:
    app = create_app(tmp_path / "data", clock=clock, sandbox=False)
    return TestClient(app, base_url="http://127.0.0.1:8765", headers={"X-GOTCHA": "1"})


def upload(client: TestClient, name: str, data: bytes) -> dict:  # type: ignore[type-arg]
    r = client.post("/api/import", files=[("files", (name, data))])
    assert r.status_code == 200, r.text
    return r.json()["results"][0]  # type: ignore[no-any-return]


def make_exam(client: TestClient) -> tuple[str, str]:
    batch_id = upload(client, "a.txt", TXT)["batch_id"]
    exam_id = client.post(f"/api/batches/{batch_id}/confirm", json={"exam_name": "Meu"}).json()["exam_id"]
    return batch_id, exam_id


# --- segurança local ----------------------------------------------------------------------------


def test_foreign_host_is_rejected(client: TestClient) -> None:
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400


def test_localhost_hosts_are_accepted(client: TestClient) -> None:
    for host in ("127.0.0.1:8765", "localhost:8765", "localhost"):
        assert client.get("/api/health", headers={"Host": host}).status_code == 200


def test_state_changing_request_requires_custom_header(client: TestClient) -> None:
    r = client.post("/api/exams/x", headers={"X-GOTCHA": ""})
    assert r.status_code == 403


def test_cross_origin_post_is_rejected(client: TestClient) -> None:
    r = client.post("/api/simulados", json={}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_same_origin_post_is_allowed(client: TestClient) -> None:
    r = client.post("/api/simulados", json={}, headers={"Origin": "http://127.0.0.1:8765"})
    assert r.status_code != 403


# --- importação e revisão -------------------------------------------------------------------


def test_import_creates_draft_not_questions(client: TestClient) -> None:
    result = upload(client, "a.txt", TXT)
    assert result["ok"] and result["format"] == "txt" and result["count"] == 3
    assert client.get("/api/exams").json() == []
    batch = client.get(f"/api/batches/{result['batch_id']}").json()
    assert batch["status"] == "draft" and len(batch["questions"]) == 3


def test_multiple_files_make_separate_batches_and_report_errors(client: TestClient) -> None:
    vce = bytes.fromhex("85a80304") + b"\x00" * 50
    r = client.post(
        "/api/import",
        files=[
            ("files", ("a.txt", TXT)),
            ("files", ("b.vce", vce)),
            ("files", ("c.bin", b"\x00xyz")),
        ],
    )
    results = r.json()["results"]
    assert [x["ok"] for x in results] == [True, False, False]
    assert "PDF" in results[1]["error"]
    assert len(client.get("/api/batches").json()) == 1


def test_zip_with_images_import(client: TestClient) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("p.html", page(card(1, stem="Arraste", answer_img="r.png")))
        z.writestr("p_files/r.png", imgs.png())
    result = upload(client, "pacote.zip", buf.getvalue())
    q = client.get(f"/api/batches/{result['batch_id']}").json()["questions"][0]
    assert q["images"][0]["sha"] and client.get(f"/api/assets/{q['images'][0]['sha']}").status_code == 200


def test_assets_are_served_safely(client: TestClient) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("p.html", page(card(1, answer_img="r.png")))
        z.writestr("r.png", imgs.png())
    result = upload(client, "p.zip", buf.getvalue())
    sha = client.get(f"/api/batches/{result['batch_id']}").json()["questions"][0]["images"][0]["sha"]
    r = client.get(f"/api/assets/{sha}")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-type"] == "image/png"
    assert client.get("/api/assets/naoexiste").status_code == 404


def test_edit_draft_sanitizes_and_updates_warnings(client: TestClient) -> None:
    batch_id = upload(client, "a.txt", TXT)["batch_id"]
    r = client.patch(
        f"/api/batches/{batch_id}/questions/0",
        json={"stem": "<p>novo</p><script>x()</script>", "answer": ["B"]},
    )
    assert r.status_code == 200
    q = r.json()
    assert "script" not in q["stem"] and q["answer"] == ["B"]
    assert client.patch(f"/api/batches/{batch_id}/questions/0", json={"id": "x"}).status_code == 400


def test_confirm_dedupes_and_undo(client: TestClient) -> None:
    batch_id, exam_id = make_exam(client)
    again = upload(client, "b.txt", TXT)["batch_id"]
    result = client.post(f"/api/batches/{again}/confirm", json={"exam_id": exam_id}).json()
    assert result["added"] == 0 and result["skipped"] == 3
    assert client.get("/api/exams").json()[0]["question_count"] == 3
    assert client.post(f"/api/batches/{batch_id}/undo").status_code == 200
    assert client.get("/api/exams").json()[0]["question_count"] == 0


def test_rename_delete_and_export_exam(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    assert client.patch(f"/api/exams/{exam_id}", json={"name": "Novo"}).status_code == 200
    assert client.get("/api/exams").json()[0]["name"] == "Novo"
    exported = client.get(f"/api/exams/{exam_id}/export")
    assert exported.status_code == 200 and exported.headers["content-type"] == "application/zip"
    assert exported.headers["content-disposition"].endswith('.gotcha"')
    again = upload(client, "sem_extensao", exported.content)  # reconhecido pelo conteúdo
    assert again["format"] == "gotcha" and again["count"] == 3
    assert client.delete(f"/api/exams/{exam_id}").status_code == 200
    assert client.get("/api/exams").json() == []


# --- prova ---------------------------------------------------------------------------------------


def start(client: TestClient, exam_id: str, **extra: object) -> str:
    spec = {"exam_ids": [exam_id], "shuffle": False, "mode": "exam", **extra}
    r = client.post("/api/simulados", json=spec)
    assert r.status_code == 200, r.text
    return r.json()["session_id"]  # type: ignore[no-any-return]


def test_exam_mode_never_sends_the_answer_key(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    sid = start(client, exam_id)
    body = client.get(f"/api/sessions/{sid}").text
    for leaked in ('"correct"', '"explanation"', '"key"', '"answer_sequence"', '"completion"'):
        assert leaked not in body


def test_exam_mode_blocks_solution_until_finished(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    sid = start(client, exam_id)
    qid = client.get(f"/api/sessions/{sid}").json()["questions"][0]["id"]
    assert client.get(f"/api/sessions/{sid}/solution/{qid}").status_code == 403
    client.post(f"/api/sessions/{sid}/finish")
    assert client.get(f"/api/sessions/{sid}/solution/{qid}").status_code == 200


def test_study_mode_reveals_on_request(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    sid = start(client, exam_id, mode="study")
    qid = client.get(f"/api/sessions/{sid}").json()["questions"][0]["id"]
    assert client.get(f"/api/sessions/{sid}/solution/{qid}").json()["key"]["correct"] == "A"


def test_full_flow_result(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    sid = start(client, exam_id)
    qs = client.get(f"/api/sessions/{sid}").json()["questions"]
    client.put(f"/api/sessions/{sid}/responses/{qs[0]['id']}", json={"selected": ["A"]})
    client.put(f"/api/sessions/{sid}/responses/{qs[1]['id']}", json={"selected": ["A"]})
    client.put(f"/api/sessions/{sid}/responses/{qs[2]['id']}", json={"self_mark": True})
    client.put(f"/api/sessions/{sid}/marks/{qs[1]['id']}", json={"marked": True})
    result = client.post(f"/api/sessions/{sid}/finish").json()
    assert result["summary"]["auto_total"] == 2 and result["summary"]["auto_correct"] == 1
    assert result["summary"]["self_pct"] == 100.0
    assert result["details"][1]["outcome"] == "incorrect"
    assert result["details"][1]["key"]["correct"] == ["A", "C"]
    assert client.get("/api/sessions").json()[0]["auto_pct"] == 50.0


def test_timer_and_expiry(client: TestClient, clock: FakeClock) -> None:
    _, exam_id = make_exam(client)
    sid = start(client, exam_id, time_limit_minutes=1)
    qid = client.get(f"/api/sessions/{sid}").json()["questions"][0]["id"]
    assert client.get(f"/api/sessions/{sid}").json()["remaining_seconds"] == 60
    clock.t += 61
    r = client.put(f"/api/sessions/{sid}/responses/{qid}", json={"selected": ["A"]})
    assert r.status_code == 409


def test_empty_simulado_is_a_clear_error(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    r = client.post("/api/simulados", json={"exam_ids": [exam_id], "only": "wrong"})
    assert r.status_code == 400 and "vazio" in r.json()["detail"]


def test_wrong_only_simulado_after_a_mistake(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    sid = start(client, exam_id)
    qs = client.get(f"/api/sessions/{sid}").json()["questions"]
    client.put(f"/api/sessions/{sid}/responses/{qs[0]['id']}", json={"selected": ["B"]})
    client.post(f"/api/sessions/{sid}/finish")
    sid2 = start(client, exam_id, only="wrong")
    assert [q["id"] for q in client.get(f"/api/sessions/{sid2}").json()["questions"]] == [qs[0]["id"]]


def test_interactive_question_can_reveal_its_answer_in_exam_mode(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    sid = start(client, exam_id)
    questions = client.get(f"/api/sessions/{sid}").json()["questions"]
    interactive = next(q for q in questions if q["type"] == "self_assessed")
    single = next(q for q in questions if q["type"] == "multiple_choice")
    assert client.get(f"/api/sessions/{sid}/solution/{interactive['id']}").status_code == 200
    assert client.get(f"/api/sessions/{sid}/solution/{single['id']}").status_code == 403


def test_result_carries_the_spec_to_repeat_only_the_wrong_ones(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    sid = start(client, exam_id)
    result = client.post(f"/api/sessions/{sid}/finish").json()
    assert result["spec"]["exam_ids"] == [exam_id]
    assert client.get(f"/api/sessions/{sid}/result").json()["spec"]["mode"] == "exam"


def test_confirmed_questions_are_listed_and_editable(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    listed = client.get(f"/api/exams/{exam_id}/questions").json()
    assert [q["type"] for q in listed] == ["multiple_choice", "multiple_select", "self_assessed"]
    uid = listed[0]["id"]
    full = client.get(f"/api/questions/{uid}").json()
    assert full["correct"] == "A"
    full["correct"] = "B"
    assert client.put(f"/api/questions/{uid}", json=full).status_code == 200
    assert client.get(f"/api/questions/{uid}").json()["correct"] == "B"


def test_invalid_edits_are_refused_with_a_clear_message(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    uid = client.get(f"/api/exams/{exam_id}/questions").json()[0]["id"]
    full = client.get(f"/api/questions/{uid}").json()
    full["correct"] = "zzz"
    r = client.put(f"/api/questions/{uid}", json=full)
    assert r.status_code == 400 and "gabarito" in r.json()["detail"]
    r = client.put(f"/api/questions/{uid}", json={"type": "tipo_inventado", "number": 1})
    assert r.status_code == 400


def test_a_question_can_be_converted_to_another_type_in_the_editor(client: TestClient) -> None:
    _, exam_id = make_exam(client)
    uid = client.get(f"/api/exams/{exam_id}/questions").json()[2]["id"]  # self_assessed vindo do import
    sha = client.post("/api/assets", files={"file": ("mapa.png", imgs.png(100, 50))}).json()["id"]
    full = client.get(f"/api/questions/{uid}").json()
    hot = {
        **{k: full[k] for k in ("uid", "topic", "number", "prompt", "explanation", "exam_id")},
        "type": "hot_area", "image": {"type": "image", "asset": sha, "alt": "mapa"}, "aspect": 0.5,
        "shapes": [
            {"id": "s1", "label": "A", "geometry": {"kind": "rect", "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3}}
        ],
        "correct": ["s1"],
    }  # fmt: skip
    assert client.put(f"/api/questions/{uid}", json=hot).status_code == 200
    assert client.get(f"/api/exams/{exam_id}/questions").json()[2]["type"] == "hot_area"


def test_asset_upload_reports_dimensions_and_dedupes(client: TestClient) -> None:
    data = imgs.png(64, 32)
    first = client.post("/api/assets", files={"file": ("a.png", data)}).json()
    second = client.post("/api/assets", files={"file": ("b.png", data)}).json()
    assert first["id"] == second["id"] and (first["width"], first["height"]) == (64, 32)
    assert second["names"] == ["a.png", "b.png"]
    assert client.post("/api/assets", files={"file": ("x.txt", b"nao e imagem")}).status_code == 400
    assert first["id"] in client.get("/api/assets/orphans").json()


CASE_TXT = b"""Q1
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
"""


def test_case_study_can_be_read_and_edited(client: TestClient) -> None:
    batch_id = upload(client, "caso.txt", CASE_TXT)["batch_id"]
    exam_id = client.post(f"/api/batches/{batch_id}/confirm", json={"exam_name": "Caso"}).json()["exam_id"]
    case_id = client.get(f"/api/exams/{exam_id}/questions").json()[0]["case_id"]
    case = client.get(f"/api/cases/{case_id}").json()
    assert len(case["question_ids"]) == 2 and "dois escritorios" in str(case["sections"])
    case["sections"][0]["title"] = "Resumo"
    assert client.put(f"/api/cases/{case_id}", json=case).status_code == 200
    assert client.get(f"/api/cases/{case_id}").json()["sections"][0]["title"] == "Resumo"
