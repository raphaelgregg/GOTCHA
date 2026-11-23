"""Pacote `.gotcha`: exportação e reimportação sem perdas, sem duplicar e sem arquivos externos."""

import io
import json
import zipfile

import pytest

from gotcha.domain.models import ParsedBatch
from gotcha.qtypes import parse_question, validate_question
from gotcha.qtypes.blocks import HtmlBlock
from gotcha.qtypes.case import CaseSection, CaseStudyDoc
from gotcha.qtypes.package import PackageError, export_package, read_package
from gotcha.storage.db import Database
from gotcha.storage.library import Library
from tests import imgs
from tests import qfactory as f


def new_lib(tmp_path, name: str) -> Library:  # type: ignore[no-untyped-def]
    return Library(Database(tmp_path / f"{name}.db"))


def populate(lib: Library) -> tuple[str, dict[str, str]]:
    """Cria um exame com um exemplar de cada tipo, imagens compartilhadas e um estudo de caso."""
    a, b = (
        lib.put_asset(imgs.png(40, 20), name="a.png"),
        lib.put_asset(imgs.png(10, 10, "blue"), name="b.png"),
    )
    svg = lib.put_asset(imgs.SVG, name="d.svg")
    exam_id = lib.create_exam("Meu exame")
    case_id = lib.create_case(
        exam_id,
        CaseStudyDoc(
            id="c",
            title="Empresa X",
            sections=[
                CaseSection(id="s1", title="Visão geral", blocks=[HtmlBlock(html="<p>Contexto único</p>")])
            ],
        ),
    )
    shared = {"type": "image", "asset": a, "alt": "diagrama"}
    for i, name in enumerate(f.ALL, start=1):
        extra: dict = {"prompt": [*f.RAW[name]["prompt"], shared], "number": i, "exam_id": exam_id}  # type: ignore[type-arg]
        if name == "hot_area":
            extra["image"] = {"type": "image", "asset": b, "alt": "mapa"}
        if name == "multiple_choice":
            extra["case_id"] = case_id
        if name == "multiple_select":
            extra["case_id"] = case_id
            extra["options"] = [
                {"id": "a", "blocks": [f.para("um"), {"type": "image", "asset": svg, "alt": "s"}]},
                *f.RAW[name]["options"][1:],
            ]
        lib.add_question(f.make(name, **extra))
    return exam_id, {"a": a, "b": b, "svg": svg}


def test_export_then_import_into_an_empty_library_preserves_everything(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src, dst = new_lib(tmp_path, "src"), new_lib(tmp_path, "dst")
    exam_id, shas = populate(src)
    package = export_package(src, exam_id)

    draft = dst.import_package(package)
    result = dst.confirm_batch(draft.id, exam_name="Importado")
    assert result.added == len(f.ALL) and result.skipped == 0

    original = {q.fingerprint(): q for q in src.questions([exam_id])}
    restored = {q.fingerprint(): q for q in dst.questions([result.exam_id])}
    assert set(original) == set(restored)  # critérios 3, 5, 6, 7, 8: o conteúdo é idêntico
    for fp, q in original.items():
        assert restored[fp].model_dump(exclude={"uid", "exam_id", "batch_id", "case_id"}) == q.model_dump(
            exclude={"uid", "exam_id", "batch_id", "case_id"}
        )
        assert validate_question(restored[fp]) == []
    for sha in shas.values():  # critério 3: as imagens são preservadas (mesmos bytes originais)
        assert dst.get_asset(sha) == src.get_asset(sha)
    assert dst.asset_refs(shas["a"]) == len(f.ALL)  # critério 2: uma imagem, várias referências


def test_package_is_self_contained(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src = new_lib(tmp_path, "src")
    exam_id, _ = populate(src)
    package = export_package(src, exam_id)
    content = read_package(package)  # só os bytes: nenhuma pasta nem arquivo externo
    assert len(content.questions) == len(f.ALL) and len(content.assets) == 3
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        names = z.namelist()
        assert "manifest.json" in names and any(n.startswith("assets/") for n in names)
        assert not any("http" in n for n in names)


def test_case_study_context_is_stored_once_and_referenced(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src, dst = new_lib(tmp_path, "src"), new_lib(tmp_path, "dst")
    exam_id, _ = populate(src)
    package = export_package(src, exam_id)
    with zipfile.ZipFile(io.BytesIO(package)) as z:
        assert len([n for n in z.namelist() if n.startswith("cases/")]) == 1
    exam2 = dst.confirm_batch(dst.import_package(package).id, exam_name="X").exam_id
    linked = [q for q in dst.questions([exam2]) if q.case_id]
    assert len(linked) == 2 and len({q.case_id for q in linked}) == 1
    assert "Contexto único" in dst.get_case(linked[0].case_id or "").sections[0].blocks[0].html  # type: ignore[union-attr]


def test_reimport_does_not_duplicate_questions_or_assets_or_cases(tmp_path) -> None:  # type: ignore[no-untyped-def]
    lib = new_lib(tmp_path, "lib")
    exam_id, _ = populate(lib)
    package = export_package(lib, exam_id)
    assets_before = lib.count_assets()
    cases_before = len(lib.list_cases(exam_id))

    result = lib.confirm_batch(lib.import_package(package).id, exam_id=exam_id)  # critério 12
    assert (result.added, result.skipped) == (0, len(f.ALL))
    assert lib.count_assets() == assets_before
    assert len(lib.list_cases(exam_id)) == cases_before
    assert lib.list_exams()[0].question_count == len(f.ALL)

    again = lib.confirm_batch(lib.import_package(package).id, exam_name="Outra cópia")  # em outro exame
    assert again.added == len(f.ALL) and lib.count_assets() == assets_before
    uids = [q.uid for e in lib.list_exams() for q in lib.questions([e.id])]
    assert len(uids) == len(set(uids))  # identificadores continuam únicos


def test_drafts_from_a_package_follow_the_review_flow(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src, dst = new_lib(tmp_path, "src"), new_lib(tmp_path, "dst")
    exam_id, _ = populate(src)
    draft = dst.import_package(export_package(src, exam_id))
    assert draft.status == "draft" and dst.list_exams() == []  # nada entra sem revisão
    assert draft.schema == 2 and len(draft.questions_v2) == len(f.ALL)


def test_tampered_asset_is_detected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src = new_lib(tmp_path, "src")
    exam_id, shas = populate(src)
    package = export_package(src, exam_id)
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package)) as zin, zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info)
            if shas["a"] in info.filename:
                data = data + b"x"
            zout.writestr(info.filename, data)
    with pytest.raises(PackageError, match="integridade"):
        read_package(out.getvalue())


def rewrite(package: bytes, edit) -> bytes:  # type: ignore[no-untyped-def]
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package)) as zin, zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            zout.writestr(info.filename, edit(info.filename, zin.read(info)))
    return out.getvalue()


def test_file_not_listed_in_the_manifest_is_refused(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src = new_lib(tmp_path, "src")
    exam_id, _ = populate(src)
    package = export_package(src, exam_id)
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package)) as zin, zipfile.ZipFile(out, "w") as zout:
        for info in zin.infolist():
            zout.writestr(info.filename, zin.read(info))
        zout.writestr("evil.exe", b"MZ")
    with pytest.raises(PackageError, match="manifesto"):
        read_package(out.getvalue())


def test_external_url_as_resource_is_refused(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src = new_lib(tmp_path, "src")
    exam_id, shas = populate(src)

    def edit(name: str, data: bytes) -> bytes:
        if name.startswith("questions/"):
            return data.replace(shas["a"].encode(), b"http://evil.example/x.png")
        return data

    # reescrever também o manifesto para passar na verificação de hash e cair na validação de conteúdo
    package = export_package(src, exam_id)
    tampered = rewrite(package, edit)
    with zipfile.ZipFile(io.BytesIO(tampered)) as z:
        manifest = json.loads(z.read("manifest.json"))
        import hashlib

        for path in manifest["files"]:
            manifest["files"][path] = hashlib.sha256(z.read(path)).hexdigest()
    final = rewrite(tampered, lambda n, d: json.dumps(manifest).encode() if n == "manifest.json" else d)
    with pytest.raises(PackageError):
        read_package(final)


def test_missing_asset_is_reported_not_silently_dropped(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src = new_lib(tmp_path, "src")
    exam_id, shas = populate(src)
    package = export_package(src, exam_id)
    stripped = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(package)) as zin, zipfile.ZipFile(stripped, "w") as zout:
        manifest = json.loads(zin.read("manifest.json"))
        for info in zin.infolist():
            if info.filename in {"manifest.json", "assets/index.json"}:
                continue
            if shas["b"] in info.filename and info.filename.startswith("assets/"):
                manifest["files"].pop(info.filename, None)
                continue
            zout.writestr(info.filename, zin.read(info))
        index = json.loads(zin.read("assets/index.json"))
        index = [a for a in index if a["id"] != shas["b"]]
        zout.writestr("assets/index.json", json.dumps(index))
        manifest["files"]["assets/index.json"] = (
            __import__("hashlib").sha256(json.dumps(index).encode()).hexdigest()
        )
        zout.writestr("manifest.json", json.dumps(manifest))
    content = read_package(stripped.getvalue())
    assert shas["b"] in content.missing_assets
    hot = next(q for q in content.questions if q.type == "hot_area")
    assert hot.conversion.status != "ok" and any(
        "ausente" in w.lower() for w in hot.conversion.warnings
    )  # critério 13


def test_zip_limits(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PackageError):
        read_package(b"nao e um zip")
    big = io.BytesIO()
    with zipfile.ZipFile(big, "w") as z:
        z.writestr("manifest.json", "{}")
        z.writestr("grande.bin", b"0" * 5_000_000)
    with pytest.raises(PackageError, match="limite"):
        read_package(big.getvalue(), max_total_bytes=1_000_000)


def test_legacy_gotcha_json_v1_is_still_importable(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gotcha.domain.models import Choice, QuestionKind
    from gotcha.domain.models import Question as V1
    from gotcha.importers import Source, detect
    from gotcha.importers.json_app import export_json

    v1 = V1(
        number=1,
        kind=QuestionKind.SINGLE,
        stem="<p>x</p>",
        choices=[Choice(letter="A", text="a"), Choice(letter="B", text="b")],
        answer=["A"],
    )
    data = export_json("antigo", [v1], [])
    src = Source(filename="antigo.json", data=data)
    assert detect(src).name == "json"
    assert isinstance(detect(src).parse(src), ParsedBatch)


def test_questions_roundtrip_through_json_for_every_type() -> None:
    for name in f.ALL:
        q = f.make(name)
        assert parse_question(json.loads(q.model_dump_json())) == q
