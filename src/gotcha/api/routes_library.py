"""Rotas de importação, revisão, biblioteca, edição de questões, estudos de caso e recursos."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

from gotcha.domain.models import Question as V1Question
from gotcha.importers import UnsupportedFormat, detect
from gotcha.importers.bundle import BundleError, load_source
from gotcha.qtypes import parse_question, public_view, summarize_question, validate_question
from gotcha.qtypes.assets import AssetError
from gotcha.qtypes.case import CaseStudyDoc
from gotcha.qtypes.package import PackageError, export_package, looks_like_package
from gotcha.qtypes.templates import convert, template
from gotcha.sandbox import SandboxError
from gotcha.storage.library import BatchView

from .services import services

router = APIRouter(prefix="/api")
MAX_FILE_BYTES = 100 * 1024 * 1024


class ConfirmBody(BaseModel):
    exam_id: str | None = None
    exam_name: str | None = None


class RenameBody(BaseModel):
    name: str


def _count_warnings(batch_warnings: list[str], questions: list[V1Question]) -> int:
    return len(batch_warnings) + sum(len(q.warnings) for q in questions)


def _v2_warnings(b: BatchView) -> int:
    return len(b.warnings) + sum(len(q.conversion.warnings) for q in b.questions_v2)


def _summary(b: BatchView) -> dict[str, Any]:
    v2 = b.schema == 2
    return {
        "id": b.id, "filename": b.filename, "format": b.format, "title": b.title,
        "status": b.status, "exam_id": b.exam_id, "schema": b.schema,
        "count": len(b.questions_v2) if v2 else len(b.questions),
        "warning_count": (
            len(b.warnings) + sum(len(q.conversion.warnings) for q in b.questions_v2)
            if v2 else _count_warnings(b.warnings, b.questions)
        ),
    }  # fmt: skip


def _detail(b: BatchView) -> dict[str, Any]:
    return {
        **_summary(b),
        "questions": [q.model_dump(mode="json") for q in b.questions],
        "cases": [c.model_dump(mode="json") for c in b.cases],
        "warnings": b.warnings,
        "questions_v2": [summarize_question(q) for q in b.questions_v2],
        "cases_v2": [{"id": c.id, "title": c.title, "sections": len(c.sections)} for c in b.cases_v2],
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/import")
def import_files(request: Request, files: list[UploadFile]) -> dict[str, Any]:
    svc = services(request)
    results: list[dict[str, Any]] = []
    for f in files:
        name = f.filename or "arquivo"
        try:
            data = f.file.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ValueError("Arquivo acima do limite de 100 MB.")
            if looks_like_package(data):
                view = svc.library.import_package(data, name)
                results.append(
                    {
                        "filename": name, "ok": True, "batch_id": view.id, "format": "gotcha",
                        "count": len(view.questions_v2),
                        "warning_count": _v2_warnings(view),
                    }
                )  # fmt: skip
                continue
            src = load_source(name, data)
            importer = detect(src)
            parsed = svc.parse(src, importer.name)
            view = svc.library.create_batch(name, parsed)
            results.append(
                {
                    "filename": name, "ok": True, "batch_id": view.id, "format": parsed.format,
                    "count": len(parsed.questions),
                    "warning_count": _count_warnings(view.warnings, parsed.questions),
                }
            )  # fmt: skip
        except (
            UnsupportedFormat,
            BundleError,
            PackageError,
            SandboxError,
            AssetError,
            ValueError,
        ) as exc:
            results.append({"filename": name, "ok": False, "error": str(exc)})
    return {"results": results}


@router.get("/batches")
def list_batches(request: Request) -> list[dict[str, Any]]:
    return [_summary(b) for b in services(request).library.list_batches() if b.status == "draft"]


@router.get("/batches/{batch_id}")
def get_batch(request: Request, batch_id: str) -> dict[str, Any]:
    return _detail(services(request).library.get_batch(batch_id))


@router.patch("/batches/{batch_id}/questions/{index}")
def edit_question(
    request: Request, batch_id: str, index: int, patch: Annotated[dict[str, Any], Body()]
) -> dict[str, Any]:
    return services(request).library.update_draft(batch_id, index, patch).model_dump(mode="json")


@router.delete("/batches/{batch_id}/questions/{index}")
def delete_question(request: Request, batch_id: str, index: int) -> dict[str, str]:
    services(request).library.delete_draft(batch_id, index)
    return {"status": "ok"}


@router.post("/batches/{batch_id}/questions/{index}/merge")
def merge_question(request: Request, batch_id: str, index: int) -> dict[str, Any]:
    return services(request).library.merge_drafts(batch_id, index).model_dump(mode="json")


@router.post("/batches/{batch_id}/confirm")
def confirm(request: Request, batch_id: str, body: ConfirmBody) -> dict[str, Any]:
    return asdict(services(request).library.confirm_batch(batch_id, body.exam_id, body.exam_name))


@router.post("/batches/{batch_id}/undo")
def undo(request: Request, batch_id: str) -> dict[str, str]:
    services(request).library.undo_batch(batch_id)
    return {"status": "ok"}


@router.delete("/batches/{batch_id}")
def discard(request: Request, batch_id: str) -> dict[str, str]:
    services(request).library.discard_batch(batch_id)
    return {"status": "ok"}


@router.get("/exams")
def list_exams(request: Request) -> list[dict[str, Any]]:
    return [asdict(e) for e in services(request).library.list_exams()]


@router.patch("/exams/{exam_id}")
def rename_exam(request: Request, exam_id: str, body: RenameBody) -> dict[str, str]:
    services(request).library.rename_exam(exam_id, body.name)
    return {"status": "ok"}


@router.delete("/exams/{exam_id}")
def delete_exam(request: Request, exam_id: str) -> dict[str, str]:
    services(request).library.delete_exam(exam_id)
    return {"status": "ok"}


@router.get("/exams/{exam_id}/export")
def export_exam(request: Request, exam_id: str) -> Response:
    """Exporta o exame como pacote `.gotcha` autossuficiente (questões, estudos de caso e mídia)."""
    try:
        data = export_package(services(request).library, exam_id)
    except KeyError as exc:
        raise HTTPException(404, "Exame não encontrado.") from exc
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{exam_id}.gotcha"'},
    )


@router.get("/exams/{exam_id}/questions")
def exam_questions(request: Request, exam_id: str) -> list[dict[str, Any]]:
    return [summarize_question(q) for q in services(request).library.questions([exam_id])]


@router.post("/exams/{exam_id}/questions")
def create_question(
    request: Request, exam_id: str, body: Annotated[dict[str, Any], Body()]
) -> dict[str, Any]:
    """Cria uma questão no exame (editor). Sem número, entra no fim do tópico."""
    lib = services(request).library
    if not any(e.id == exam_id for e in lib.list_exams()):
        raise HTTPException(404, "Exame não encontrado.")
    topic = int(body.get("topic", 1))
    data = {**body, "topic": topic, "exam_id": exam_id}
    data.pop("uid", None)
    data.setdefault("number", lib.next_number(exam_id, topic))
    question = parse_question(data)
    uid = lib.add_question(question)
    return lib.get_question(uid).model_dump(mode="json", exclude={"batch_id"})


@router.get("/questions/{uid}")
def get_question(request: Request, uid: str) -> dict[str, Any]:
    """Questão completa, com gabarito, para o editor."""
    return services(request).library.get_question(uid).model_dump(mode="json", exclude={"batch_id"})


@router.put("/questions/{uid}")
def put_question(request: Request, uid: str, body: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
    question = parse_question(body)
    return (
        services(request)
        .library.replace_question(uid, question)
        .model_dump(mode="json", exclude={"batch_id"})
    )


@router.post("/preview")
def preview_question(body: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
    """Valida uma questão em edição e devolve a visão de prova, sem salvar nada."""
    try:
        question = parse_question(body)
    except ValidationError as exc:
        errors = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:12]]
        return {"view": None, "errors": errors}
    errors = validate_question(question)
    if errors:
        return {"view": None, "errors": errors}
    return {"view": public_view(question, False, 1), "errors": []}


@router.get("/templates/{type_}")
def question_template(type_: str, mode: str = "simulated") -> dict[str, Any]:
    return template(type_, mode)


@router.post("/convert/{type_}")
def convert_question(
    type_: str, body: Annotated[dict[str, Any], Body()], mode: str = "simulated"
) -> dict[str, Any]:
    """Converte a questão para outro tipo, preservando enunciado e identidade (nada é salvo)."""
    return convert(body, type_, mode)


@router.delete("/questions/{uid}")
def remove_question(request: Request, uid: str) -> dict[str, str]:
    services(request).library.delete_question(uid)
    return {"status": "ok"}


@router.get("/cases/{case_id}")
def get_case(request: Request, case_id: str) -> dict[str, Any]:
    lib = services(request).library
    return {
        **lib.get_case(case_id).model_dump(mode="json"),
        "question_ids": lib.case_questions(case_id),
    }


@router.put("/cases/{case_id}")
def put_case(request: Request, case_id: str, body: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
    doc = CaseStudyDoc.model_validate({**body, "id": case_id})
    return services(request).library.replace_case(case_id, doc).model_dump(mode="json")


@router.post("/assets")
def upload_asset(request: Request, file: UploadFile) -> dict[str, Any]:
    """Adiciona ou substitui uma imagem no editor. O arquivo original é preservado."""
    lib = services(request).library
    data = file.file.read(26 * 1024 * 1024)
    try:
        sha = lib.put_asset(data, name=file.filename or "")
    except AssetError as exc:
        raise HTTPException(400, str(exc)) from exc
    return asdict(lib.asset_info(sha))


@router.get("/assets/orphans")
def orphan_assets(request: Request) -> list[str]:
    return services(request).library.orphan_assets()


@router.get("/assets/{sha}/info")
def asset_info(request: Request, sha: str) -> dict[str, Any]:
    return asdict(services(request).library.asset_info(sha))


@router.get("/assets/{sha}")
def asset(request: Request, sha: str) -> Response:
    found = services(request).library.get_asset_view(sha)
    if found is None:
        raise HTTPException(404, "Imagem não encontrada.")
    data, media = found
    headers = {"Cache-Control": "private, max-age=86400", "Content-Security-Policy": "sandbox"}
    if media == "application/pdf":
        headers["Content-Disposition"] = "attachment"
    return Response(data, media_type=media, headers=headers)
