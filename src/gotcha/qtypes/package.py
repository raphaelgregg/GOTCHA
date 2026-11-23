"""Pacote `.gotcha`: ZIP aberto com manifesto, JSON por questão e mídia embutida.

Autossuficiente (sem URLs externas), verificado por SHA-256 e lido com limites contra ZIP malicioso.
Nada do pacote é executado.
"""

from __future__ import annotations

import hashlib
import io
import json
import posixpath
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from . import parse_question
from .assets import sniff_mime
from .base import QuestionBase
from .case import CaseStudyDoc

if TYPE_CHECKING:
    from gotcha.storage.library import Library

FORMAT = "gotcha"
FORMAT_VERSION = 1
APP_VERSION = "0.1.0"
MAX_TOTAL = 2 * 1024 * 1024 * 1024
MAX_MEMBERS = 50_000
_EXT = {
    "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif",
    "image/svg+xml": "svg", "application/pdf": "pdf",
}  # fmt: skip
_FIXED_TIME = (2020, 1, 1, 0, 0, 0)


class PackageError(ValueError):
    """Pacote inválido, adulterado ou acima dos limites."""


@dataclass
class PackageContent:
    manifest: dict[str, Any]
    exam: dict[str, Any]
    questions: list[QuestionBase]
    cases: list[CaseStudyDoc]
    assets: dict[str, bytes]  # sha -> bytes originais
    asset_names: dict[str, str] = field(default_factory=dict)
    missing_assets: list[str] = field(default_factory=list)

    @property
    def title(self) -> str:
        return str(self.manifest.get("title", ""))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dumps(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def _asset_path(sha: str, mime: str) -> str:
    return f"assets/{sha[:2]}/{sha}.{_EXT.get(mime, 'bin')}"


def export_package(lib: Library, exam_id: str) -> bytes:
    from gotcha.storage.library import collect_assets

    exam = next((e for e in lib.list_exams() if e.id == exam_id), None)
    if exam is None:
        raise KeyError(exam_id)
    questions = lib.questions([exam_id])
    case_ids = sorted({q.case_id for q in questions if q.case_id})
    cases = [lib.get_case(c) for c in case_ids]
    files: dict[str, bytes] = {}

    for q in questions:
        files[f"questions/{q.uid}.json"] = _dumps(q.model_dump(mode="json", exclude={"exam_id", "batch_id"}))
    for case in cases:
        owners = [q.uid for q in questions if q.case_id == case.id]
        files[f"cases/{case.id}.json"] = _dumps({**case.model_dump(mode="json"), "question_uids": owners})
    shas: set[str] = set()
    for q in questions:
        shas |= collect_assets(q.model_dump(mode="json"))
    for case in cases:
        shas |= collect_assets(case.model_dump(mode="json"))

    index: list[dict[str, Any]] = []
    for sha in sorted(shas):
        original = lib.get_asset(sha)
        if original is None:
            continue
        info = lib.asset_info(sha)
        view = lib.get_asset_view(sha)
        path = _asset_path(sha, info.mime)
        entry: dict[str, Any] = {
            "id": sha, "names": info.names, "mime": info.mime, "width": info.width, "height": info.height,
            "pages": info.pages, "size": info.size, "path": path, "default_alt": info.default_alt,
            "origin": info.origin, "conversion": info.conversion,
        }  # fmt: skip
        if view is not None and view[0] != original:  # SVG: original guardado, mas nunca exibido
            files[path] = view[0]
            entry["original_path"] = f"originals/{sha}.{_EXT.get(info.mime, 'bin')}"
            files[entry["original_path"]] = original
        else:
            files[path] = original
        index.append(entry)
    files["assets/index.json"] = _dumps(index)
    files["exam.json"] = _dumps(
        {"name": exam.name, "topics": exam.topics, "order": [q.uid for q in questions]}
    )
    manifest = {
        "format": FORMAT, "format_version": FORMAT_VERSION, "app_version": APP_VERSION,
        "package_id": uuid.uuid4().hex, "title": exam.name,
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "counts": {"questions": len(questions), "cases": len(cases), "assets": len(index)},
        "files": {path: _sha(data) for path, data in sorted(files.items())},
    }  # fmt: skip
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in ["manifest.json", *sorted(files)]:
            data = _dumps(manifest) if path == "manifest.json" else files[path]
            zinfo = zipfile.ZipInfo(path, _FIXED_TIME)
            already_compressed = path.startswith(("assets/", "originals/")) and not path.endswith(
                (".svg", "index.json")
            )
            zinfo.compress_type = zipfile.ZIP_STORED if already_compressed else zipfile.ZIP_DEFLATED
            z.writestr(zinfo, data)
    return out.getvalue()


def looks_like_package(data: bytes) -> bool:
    """Reconhece um pacote `.gotcha` pelo conteúdo (ZIP com manifesto do formato), não pela extensão."""
    if not data.startswith(b"PK") or not zipfile.is_zipfile(io.BytesIO(data)):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return (
                "manifest.json" in z.namelist()
                and json.loads(z.read("manifest.json")).get("format") == FORMAT
            )
    except (zipfile.BadZipFile, json.JSONDecodeError, KeyError):
        return False


def _safe_name(name: str) -> bool:
    norm = posixpath.normpath(name)
    return not (name.startswith("/") or "\\" in name or norm.startswith("..") or ".." in norm.split("/"))


def _mark_missing(node: Any, missing: set[str], names: dict[str, str]) -> bool:
    """Troca referências a recursos ausentes por anexo ausente (nunca descarta em silêncio)."""
    changed = False
    if isinstance(node, dict):
        if node.get("asset") in missing:
            node["name"] = node.get("name") or names.get(node["asset"], node["asset"][:8])
            node["asset"] = None
            changed = True
        for v in node.values():
            changed = _mark_missing(v, missing, names) or changed
    elif isinstance(node, list):
        for v in node:
            changed = _mark_missing(v, missing, names) or changed
    return changed


def read_package(data: bytes, max_total_bytes: int = MAX_TOTAL) -> PackageContent:
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise PackageError("Arquivo inválido: não é um pacote .gotcha.")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(infos) > MAX_MEMBERS or sum(i.file_size for i in infos) > max_total_bytes:
            raise PackageError("O pacote excede o limite de tamanho ou de quantidade de arquivos.")
        if len(set(names)) != len(names):
            raise PackageError("O pacote tem arquivos com nome repetido.")
        if not all(_safe_name(n) for n in names):
            raise PackageError("O pacote contém caminhos inseguros.")
        if "manifest.json" not in names:
            raise PackageError("O pacote não tem manifesto.")
        try:
            manifest = json.loads(z.read("manifest.json"))
        except json.JSONDecodeError as exc:
            raise PackageError(f"Manifesto inválido: {exc}") from exc
        if manifest.get("format") != FORMAT or int(manifest.get("format_version", 0)) > FORMAT_VERSION:
            raise PackageError("Formato ou versão de pacote não suportado.")
        listed: dict[str, str] = manifest.get("files", {})
        extra = [n for n in names if n != "manifest.json" and n not in listed]
        if extra:
            raise PackageError(f"Arquivo fora do manifesto: {extra[0]}.")
        blobs: dict[str, bytes] = {}
        for path, digest in listed.items():
            if path not in names:
                raise PackageError(f"Arquivo listado no manifesto está ausente: {path}.")
            blob = z.read(path)
            if _sha(blob) != digest:
                raise PackageError(f"Falha de integridade em {path}.")
            blobs[path] = blob

    index: list[dict[str, Any]] = json.loads(blobs.get("assets/index.json", b"[]"))
    assets: dict[str, bytes] = {}
    asset_names: dict[str, str] = {}
    for entry in index:
        path = entry.get("original_path") or entry["path"]
        if path in blobs:
            assets[entry["id"]] = blobs[path]
            asset_names[entry["id"]] = (entry.get("names") or [""])[0]
    exam = json.loads(blobs.get("exam.json", b"{}"))
    order = exam.get("order", [])
    q_paths = sorted(
        (p for p in blobs if p.startswith("questions/")),
        key=lambda p: (order.index(p[10:-5]) if p[10:-5] in order else len(order), p),
    )
    raw_questions = [json.loads(blobs[p]) for p in q_paths]
    raw_cases = [json.loads(blobs[p]) for p in sorted(p for p in blobs if p.startswith("cases/"))]

    referenced: set[str] = set()
    from gotcha.storage.library import collect_assets

    for obj in [*raw_questions, *raw_cases]:
        referenced |= collect_assets(obj)
    missing = sorted(
        sha
        for sha in referenced
        if sha not in assets and len(sha) == 64 and set(sha) <= set("0123456789abcdef")
    )
    missing_set = set(missing)
    questions: list[QuestionBase] = []
    for path, raw in zip(q_paths, raw_questions, strict=True):
        changed = _mark_missing(raw, missing_set, asset_names)
        try:
            q = parse_question(raw)
        except ValidationError as exc:
            raise PackageError(f"Questão inválida em {path}: {exc.errors()[0]['msg']}") from exc
        if changed:
            q.conversion.status = "partial" if q.conversion.status == "ok" else q.conversion.status
            q.conversion.warnings.append(
                "Recurso ausente no pacote: a imagem foi marcada como anexo ausente."
            )
        questions.append(q)
    cases: list[CaseStudyDoc] = []
    for raw in raw_cases:
        _mark_missing(raw, missing_set, asset_names)
        raw.pop("question_uids", None)
        try:
            cases.append(CaseStudyDoc.model_validate(raw))
        except ValidationError as exc:
            raise PackageError(f"Estudo de caso inválido: {exc.errors()[0]['msg']}") from exc
    for sha, blob in assets.items():
        if sniff_mime(blob) is None:
            raise PackageError(f"Recurso {sha[:8]}… com tipo não permitido.")
    return PackageContent(manifest, exam, questions, cases, assets, asset_names, missing)
