"""Rotas de importação, revisão, confirmação e biblioteca de exames."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from gotcha.domain.models import Question
from gotcha.importers import UnsupportedFormat, detect
from gotcha.importers.bundle import BundleError, load_source
from gotcha.importers.json_app import export_json
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


def _count_warnings(batch_warnings: list[str], questions: list[Question]) -> int:
    return len(batch_warnings) + sum(len(q.warnings) for q in questions)


def _summary(b: BatchView) -> dict[str, Any]:
    return {
        "id": b.id, "filename": b.filename, "format": b.format, "title": b.title,
        "status": b.status, "exam_id": b.exam_id, "count": len(b.questions),
        "warning_count": _count_warnings(b.warnings, b.questions),
    }  # fmt: skip


def _detail(b: BatchView) -> dict[str, Any]:
    return {
        **_summary(b),
        "questions": [q.model_dump(mode="json") for q in b.questions],
        "cases": [c.model_dump(mode="json") for c in b.cases],
        "warnings": b.warnings,
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
            src = load_source(name, data)
            importer = detect(src)
            parsed = svc.parse(src, importer.name)
            view = svc.library.create_batch(name, parsed)
            results.append(
                {
                    "filename": name, "ok": True, "batch_id": view.id, "format": parsed.format,
                    "count": len(parsed.questions),
                    "warning_count": _count_warnings(parsed.warnings, parsed.questions),
                }
            )  # fmt: skip
        except (UnsupportedFormat, BundleError, SandboxError, ValueError) as exc:
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
    q = services(request).library.update_draft(batch_id, index, patch)
    return q.model_dump(mode="json")


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
    lib = services(request).library
    exam = next((e for e in lib.list_exams() if e.id == exam_id), None)
    if exam is None:
        raise HTTPException(404, "Exame não encontrado.")
    questions = lib.questions([exam_id])
    cases = [lib.get_case(c) for c in sorted({q.case_id for q in questions if q.case_id})]
    return Response(
        export_json(exam.name, questions, cases),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{exam_id}.gotcha.json"'},
    )


_MAGIC = [
    (b"\x89PNG", "image/png"), (b"\xff\xd8\xff", "image/jpeg"), (b"GIF8", "image/gif"),
    (b"RIFF", "image/webp"), (b"<svg", "image/svg+xml"),
]  # fmt: skip


@router.get("/assets/{sha}")
def asset(request: Request, sha: str) -> Response:
    data = services(request).library.get_asset(sha)
    if data is None:
        raise HTTPException(404, "Imagem não encontrada.")
    media = next(
        (m for magic, m in _MAGIC if data.lstrip()[:8].startswith(magic)),
        "application/octet-stream",
    )
    headers = {"Cache-Control": "private, max-age=86400", "Content-Security-Policy": "sandbox"}
    return Response(data, media_type=media, headers=headers)
