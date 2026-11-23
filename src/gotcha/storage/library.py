"""Biblioteca: rascunhos, exames, questões v2 confirmadas, estudos de caso e recursos."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from gotcha.domain.models import CaseStudy, Choice, ParsedBatch, Question
from gotcha.domain.sanitize import clean_html
from gotcha.importers.common import infer_kind, validate_answer
from gotcha.qtypes import parse_question, validate_question
from gotcha.qtypes.assets import AssetError, analyze
from gotcha.qtypes.base import QuestionBase, new_uid
from gotcha.qtypes.blocks import HtmlBlock
from gotcha.qtypes.case import CaseSection, CaseStudyDoc
from gotcha.qtypes.migrate import load_question, v1_to_v2

from .db import Database

EDITABLE = {"topic", "number", "kind", "stem", "choices", "answer", "explanation"}
_STALE_WARNINGS = ("Sem gabarito", "O gabarito cita")


class DraftPayload(BaseModel):
    """O que fica salvo de um lote em rascunho (esquema 1: importadores; esquema 2: pacote .gotcha)."""

    schema_version: int = 1
    questions: list[Question] = Field(default_factory=list)
    cases: list[CaseStudy] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    questions_v2: list[dict[str, Any]] = Field(default_factory=list)
    cases_v2: list[CaseStudyDoc] = Field(default_factory=list)


@dataclass
class BatchView:
    id: str
    filename: str
    format: str
    title: str
    status: str
    exam_id: str | None
    schema: int
    questions: list[Question]
    cases: list[CaseStudy]
    warnings: list[str]
    questions_v2: list[QuestionBase] = field(default_factory=list)
    cases_v2: list[CaseStudyDoc] = field(default_factory=list)


@dataclass
class ExamInfo:
    id: str
    name: str
    question_count: int
    topics: list[int]


@dataclass
class ConfirmResult:
    exam_id: str
    added: int
    skipped: int
    renumbered: int = 0


@dataclass
class AssetRecord:
    id: str
    mime: str
    width: int | None
    height: int | None
    pages: int | None
    size: int
    names: list[str]
    origin: dict[str, Any]
    conversion: dict[str, Any]
    default_alt: str


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def collect_assets(value: Any) -> set[str]:
    """Todos os recursos referenciados por um objeto JSON (qualquer chave `asset`)."""
    found: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "asset" and isinstance(v, str):
                found.add(v)
            else:
                found |= collect_assets(v)
    elif isinstance(value, list):
        for v in value:
            found |= collect_assets(v)
    return found


def case_from_v1(case: CaseStudy) -> CaseStudyDoc:
    return CaseStudyDoc(
        id=case.id,
        title=case.title,
        sections=[CaseSection(id="contexto", title="Contexto", blocks=[HtmlBlock(html=case.text)])],
    )


class Library:
    def __init__(self, db: Database, clock: Callable[[], float] = time.time) -> None:
        self.db = db
        self.clock = clock

    # --- recursos ------------------------------------------------------------------------------
    def put_asset(self, data: bytes, name: str = "", origin: dict[str, Any] | None = None) -> str:
        info = analyze(data)
        row = self.db.one("SELECT names FROM assets WHERE sha = ?", (info.sha,))
        if row is not None:
            names = json.loads(row["names"] or "[]")
            if name and name not in names:
                names.append(name)
                self.db.execute("UPDATE assets SET names = ? WHERE sha = ?", (json.dumps(names), info.sha))
            return info.sha
        conversion = (
            {"operation": "sanitize_svg", "lossless": False, "derived_from": info.sha}
            if info.view_data is not None
            else {}
        )
        self.db.execute(
            "INSERT INTO assets (sha, data, mime, width, height, pages, size, view_data, names,"
            " origin, conversion, default_alt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '')",
            (
                info.sha, data, info.mime, info.width, info.height, info.pages, info.size,
                info.view_data, json.dumps([name] if name else []), json.dumps(origin or {}),
                json.dumps(conversion),
            ),
        )  # fmt: skip
        return info.sha

    def get_asset(self, sha: str) -> bytes | None:
        """Bytes originais, nunca alterados."""
        row = self.db.one("SELECT data FROM assets WHERE sha = ?", (sha,))
        return bytes(row["data"]) if row else None

    def get_asset_view(self, sha: str) -> tuple[bytes, str] | None:
        """Bytes que podem ser exibidos (SVG sanitizado) e o tipo MIME."""
        row = self.db.one("SELECT data, view_data, mime FROM assets WHERE sha = ?", (sha,))
        if row is None:
            return None
        data = row["view_data"] if row["view_data"] is not None else row["data"]
        return bytes(data), row["mime"] or "application/octet-stream"

    def asset_info(self, sha: str) -> AssetRecord:
        row = self.db.one("SELECT * FROM assets WHERE sha = ?", (sha,))
        if row is None:
            raise KeyError(sha)
        return AssetRecord(
            id=row["sha"], mime=row["mime"] or "", width=row["width"], height=row["height"],
            pages=row["pages"], size=row["size"] or 0, names=json.loads(row["names"] or "[]"),
            origin=json.loads(row["origin"] or "{}"), conversion=json.loads(row["conversion"] or "{}"),
            default_alt=row["default_alt"] or "",
        )  # fmt: skip

    def count_assets(self) -> int:
        row = self.db.one("SELECT COUNT(*) AS n FROM assets")
        return int(row["n"]) if row else 0

    def asset_refs(self, sha: str) -> int:
        row = self.db.one("SELECT COUNT(DISTINCT owner) AS n FROM asset_refs WHERE sha = ?", (sha,))
        return int(row["n"]) if row else 0

    def orphan_assets(self) -> list[str]:
        rows = self.db.query("SELECT sha FROM assets WHERE sha NOT IN (SELECT sha FROM asset_refs)")
        return [r["sha"] for r in rows]

    def _set_refs(self, owner: str, shas: set[str]) -> None:
        self.db.execute("DELETE FROM asset_refs WHERE owner = ?", (owner,))
        for sha in shas:
            self.db.execute("INSERT OR IGNORE INTO asset_refs (owner, sha) VALUES (?, ?)", (owner, sha))

    # --- lotes (rascunhos) -----------------------------------------------------------------------
    def create_batch(self, filename: str, parsed: ParsedBatch) -> BatchView:
        warnings = list(parsed.warnings)
        refused: set[str] = set()
        for sha, data in parsed.assets.items():
            try:
                self.put_asset(data, name=sha[:8])
            except AssetError as exc:
                refused.add(sha)
                warnings.append(f"Recurso recusado ({sha[:8]}…): {exc}")
        for q in parsed.questions:
            for img in q.images:
                if img.sha in refused:
                    img.sha = None
        payload = DraftPayload(questions=parsed.questions, cases=parsed.cases, warnings=warnings)
        return self._insert_batch(filename, parsed.format, parsed.title or filename, payload)

    def _insert_batch(self, filename: str, fmt: str, title: str, payload: DraftPayload) -> BatchView:
        batch_id = _new_id()
        self.db.execute(
            "INSERT INTO batches (id, filename, format, title, status, created_at, payload)"
            " VALUES (?, ?, ?, ?, 'draft', ?, ?)",
            (batch_id, filename, fmt, title, self.clock(), payload.model_dump_json()),
        )
        return self.get_batch(batch_id)

    def get_batch(self, batch_id: str) -> BatchView:
        row = self.db.one("SELECT * FROM batches WHERE id = ?", (batch_id,))
        if row is None:
            raise KeyError(batch_id)
        p = DraftPayload.model_validate_json(row["payload"])
        return BatchView(
            id=row["id"], filename=row["filename"], format=row["format"], title=row["title"],
            status=row["status"], exam_id=row["exam_id"], schema=p.schema_version,
            questions=p.questions, cases=p.cases, warnings=p.warnings,
            questions_v2=[parse_question(d) for d in p.questions_v2], cases_v2=p.cases_v2,
        )  # fmt: skip

    def list_batches(self) -> list[BatchView]:
        rows = self.db.query("SELECT id FROM batches ORDER BY created_at DESC")
        return [self.get_batch(r["id"]) for r in rows]

    def _save_draft(self, view: BatchView) -> None:
        payload = DraftPayload(
            schema_version=view.schema, questions=view.questions, cases=view.cases,
            warnings=view.warnings, questions_v2=[q.model_dump(mode="json") for q in view.questions_v2],
            cases_v2=view.cases_v2,
        )  # fmt: skip
        self.db.execute("UPDATE batches SET payload = ? WHERE id = ?", (payload.model_dump_json(), view.id))

    def _editable(self, batch_id: str) -> BatchView:
        view = self.get_batch(batch_id)
        if view.status != "draft":
            raise ValueError("Só lotes em rascunho podem ser editados.")
        if view.schema != 1:
            raise ValueError("Este lote usa o modelo novo: edite as questões depois de confirmar.")
        return view

    def update_draft(self, batch_id: str, index: int, patch: dict[str, Any]) -> Question:
        view = self._editable(batch_id)
        unknown = set(patch) - EDITABLE
        if unknown:
            raise ValueError(f"Campos não editáveis: {', '.join(sorted(unknown))}.")
        data = view.questions[index].model_dump()
        data.update(patch)
        if "stem" in patch:
            data["stem"] = clean_html(str(patch["stem"]))
        question = Question.model_validate(data)
        question.warnings = [w for w in question.warnings if not w.startswith(_STALE_WARNINGS)]
        if question.kind.value != "interactive":
            question.warnings += validate_answer(question.choices, question.answer)
        view.questions[index] = question
        self._save_draft(view)
        return question

    def delete_draft(self, batch_id: str, index: int) -> None:
        view = self._editable(batch_id)
        del view.questions[index]
        self._save_draft(view)

    def merge_drafts(self, batch_id: str, index: int) -> Question:
        """Une a questão `index` com a seguinte (ex.: questão quebrada entre páginas)."""
        view = self._editable(batch_id)
        a, b = view.questions[index], view.questions[index + 1]
        offset = len(a.choices)
        shifted = [Choice(letter=chr(ord("A") + offset + i), text=c.text) for i, c in enumerate(b.choices)]
        answer = a.answer or [chr(ord(letter) + offset - ord("A")) for letter in b.answer]
        choices = [*a.choices, *shifted]
        merged = a.model_copy(
            update={
                "stem": a.stem + b.stem, "choices": choices, "answer": answer,
                "images": [*a.images, *b.images], "warnings": [*a.warnings, *b.warnings],
                "kind": infer_kind(choices, answer),
            }
        )  # fmt: skip
        view.questions[index : index + 2] = [merged]
        self._save_draft(view)
        return merged

    # --- confirmação ---------------------------------------------------------------------------------
    def create_exam(self, name: str) -> str:
        exam_id = _new_id()
        self.db.execute(
            "INSERT INTO exams (id, name, created_at) VALUES (?, ?, ?)",
            (exam_id, name.strip(), self.clock()),
        )
        return exam_id

    def _exam_questions(self, exam_id: str) -> list[QuestionBase]:
        return self.questions([exam_id])

    def create_case(self, exam_id: str, doc: CaseStudyDoc, batch_id: str | None = None) -> str:
        case_id = _new_id()
        stored = doc.model_copy(update={"id": case_id})
        self.db.execute(
            "INSERT INTO cases (id, exam_id, batch_id, title, text, data) VALUES (?, ?, ?, ?, '', ?)",
            (case_id, exam_id, batch_id, stored.title, stored.model_dump_json()),
        )
        self._set_refs(case_id, collect_assets(stored.model_dump(mode="json")))
        return case_id

    def replace_case(self, case_id: str, doc: CaseStudyDoc) -> CaseStudyDoc:
        self.get_case(case_id)
        stored = doc.model_copy(update={"id": case_id})
        self.db.execute(
            "UPDATE cases SET title = ?, data = ? WHERE id = ?",
            (stored.title, stored.model_dump_json(), case_id),
        )
        self._set_refs(case_id, collect_assets(stored.model_dump(mode="json")))
        return stored

    def case_questions(self, case_id: str) -> list[str]:
        rows = self.db.query("SELECT id, data FROM questions")
        return [r["id"] for r in rows if load_question(r["data"]).case_id == case_id]

    def list_cases(self, exam_id: str) -> list[CaseStudyDoc]:
        rows = self.db.query("SELECT id FROM cases WHERE exam_id = ?", (exam_id,))
        return [self.get_case(r["id"]) for r in rows]

    def get_case(self, case_id: str) -> CaseStudyDoc:
        row = self.db.one("SELECT id, title, text, data FROM cases WHERE id = ?", (case_id,))
        if row is None:
            raise KeyError(case_id)
        if row["data"]:
            return CaseStudyDoc.model_validate_json(row["data"])
        return case_from_v1(CaseStudy(id=row["id"], title=row["title"] or "Estudo de caso", text=row["text"]))

    def _case_for_exam(self, exam_id: str, doc: CaseStudyDoc, batch_id: str) -> str:
        """Reaproveita um estudo de caso idêntico do exame; senão cria. Nunca duplica o contexto."""
        wanted = doc.fingerprint()
        for existing in self.list_cases(exam_id):
            if existing.fingerprint() == wanted:
                return existing.id
        return self.create_case(exam_id, doc, batch_id)

    def _insert_question(self, q: QuestionBase) -> str:
        assert q.exam_id is not None
        if self.db.one("SELECT 1 FROM questions WHERE id = ?", (q.uid,)):
            q = q.model_copy(update={"uid": new_uid()})  # mesmo uid em outro exame: nova identidade
        self.db.execute(
            "INSERT INTO questions (id, exam_id, batch_id, topic, number, data, fingerprint)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (q.uid, q.exam_id, q.batch_id, q.topic, q.number, q.model_dump_json(), q.fingerprint()),
        )
        self._set_refs(q.uid, collect_assets(q.model_dump(mode="json")))
        return q.uid

    def add_question(self, q: QuestionBase) -> str:
        """Insere uma questão já pronta (editor e testes), exigindo coerência interna."""
        errors = validate_question(q)
        if errors:
            raise ValueError("; ".join(errors))
        return self._insert_question(q)

    def replace_question(self, uid: str, q: QuestionBase) -> QuestionBase:
        old = self.get_question(uid)
        errors = validate_question(q)
        if errors:
            raise ValueError("; ".join(errors))
        q = q.model_copy(update={"uid": uid, "exam_id": old.exam_id, "batch_id": old.batch_id})
        self.db.execute(
            "UPDATE questions SET topic = ?, number = ?, data = ?, fingerprint = ? WHERE id = ?",
            (q.topic, q.number, q.model_dump_json(), q.fingerprint(), uid),
        )
        self._set_refs(uid, collect_assets(q.model_dump(mode="json")))
        return q

    def delete_question(self, uid: str) -> None:
        self.db.execute("DELETE FROM questions WHERE id = ?", (uid,))
        self.db.execute("DELETE FROM asset_refs WHERE owner = ?", (uid,))
        self.db.execute("DELETE FROM question_stats WHERE question_id = ?", (uid,))

    def _target_exam(self, exam_id: str | None, name: str, view: BatchView) -> str:
        if exam_id is None:
            return self.create_exam((name or view.title or view.filename).strip())
        if self.db.one("SELECT 1 FROM exams WHERE id = ?", (exam_id,)) is None:
            raise KeyError(exam_id)
        return exam_id

    def next_number(self, exam_id: str, topic: int) -> int:
        return self._free_number(exam_id, topic)

    def _free_number(self, exam_id: str, topic: int) -> int:
        row = self.db.one(
            "SELECT MAX(number) AS n FROM questions WHERE exam_id = ? AND topic = ?",
            (exam_id, topic),
        )
        return int(row["n"] or 0) + 1 if row else 1

    def confirm_batch(
        self, batch_id: str, exam_id: str | None = None, exam_name: str | None = None
    ) -> ConfirmResult:
        view = self.get_batch(batch_id)
        if view.status != "draft":
            raise ValueError("Só lotes em rascunho podem ser confirmados.")
        with self.db.transaction():
            target = self._target_exam(exam_id, exam_name or "", view)
            if view.schema == 2:
                added, skipped, renumbered = self._confirm_v2(view, target)
            else:
                added, skipped, renumbered = self._confirm_v1(view, target)
            self.db.execute(
                "UPDATE batches SET status = 'confirmed', exam_id = ? WHERE id = ?",
                (target, batch_id),
            )
        return ConfirmResult(exam_id=target, added=added, skipped=skipped, renumbered=renumbered)

    def _known(self, exam_id: str) -> tuple[set[tuple[int, int]], set[str], set[str]]:
        rows = self.db.query(
            "SELECT id, topic, number, fingerprint FROM questions WHERE exam_id = ?", (exam_id,)
        )
        return (
            {(r["topic"], r["number"]) for r in rows},
            {r["fingerprint"] for r in rows if r["fingerprint"]},
            {r["id"] for r in rows},
        )

    def _confirm_v1(self, view: BatchView, exam_id: str) -> tuple[int, int, int]:
        positions, prints, _ = self._known(exam_id)
        cases = {c.id: case_from_v1(c) for c in view.cases}
        mapped: dict[str, str] = {}
        added = skipped = 0
        for draft in view.questions:
            q = v1_to_v2(draft).model_copy(update={"exam_id": exam_id, "batch_id": view.id})
            if (q.topic, q.number) in positions or q.fingerprint() in prints:
                skipped += 1
                continue
            if q.case_id and q.case_id in cases:
                if q.case_id not in mapped:
                    mapped[q.case_id] = self._case_for_exam(exam_id, cases[q.case_id], view.id)
                q = q.model_copy(update={"case_id": mapped[q.case_id]})
            else:
                q = q.model_copy(update={"case_id": None})
            self._insert_question(q)
            positions.add((q.topic, q.number))
            prints.add(q.fingerprint())
            added += 1
        return added, skipped, 0

    def _confirm_v2(self, view: BatchView, exam_id: str) -> tuple[int, int, int]:
        positions, prints, uids = self._known(exam_id)
        cases = {c.id: c for c in view.cases_v2}
        mapped: dict[str, str] = {}
        added = skipped = renumbered = 0
        for draft in view.questions_v2:
            q = draft.model_copy(update={"exam_id": exam_id, "batch_id": view.id})
            if q.uid in uids or q.fingerprint() in prints:
                skipped += 1
                continue
            if q.case_id and q.case_id in cases:
                if q.case_id not in mapped:
                    mapped[q.case_id] = self._case_for_exam(exam_id, cases[q.case_id], view.id)
                q = q.model_copy(update={"case_id": mapped[q.case_id]})
            else:
                q = q.model_copy(update={"case_id": None})
            if (q.topic, q.number) in positions:
                q = q.model_copy(update={"number": self._free_number(exam_id, q.topic)})
                renumbered += 1
            self._insert_question(q)
            positions.add((q.topic, q.number))
            prints.add(q.fingerprint())
            added += 1
        return added, skipped, renumbered

    def undo_batch(self, batch_id: str) -> None:
        with self.db.transaction():
            for r in self.db.query("SELECT id FROM questions WHERE batch_id = ?", (batch_id,)):
                self.db.execute("DELETE FROM asset_refs WHERE owner = ?", (r["id"],))
                self.db.execute("DELETE FROM question_stats WHERE question_id = ?", (r["id"],))
            for r in self.db.query("SELECT id FROM cases WHERE batch_id = ?", (batch_id,)):
                self.db.execute("DELETE FROM asset_refs WHERE owner = ?", (r["id"],))
            self.db.execute("DELETE FROM questions WHERE batch_id = ?", (batch_id,))
            self.db.execute("DELETE FROM cases WHERE batch_id = ?", (batch_id,))
            self.db.execute("UPDATE batches SET status = 'undone' WHERE id = ?", (batch_id,))

    def discard_batch(self, batch_id: str) -> None:
        self.db.execute("DELETE FROM batches WHERE id = ? AND status = 'draft'", (batch_id,))

    # --- pacote .gotcha ---------------------------------------------------------------------------------
    def import_package(self, data: bytes, filename: str = "pacote.gotcha") -> BatchView:
        from gotcha.qtypes.package import PackageError, read_package

        content = read_package(data)
        for sha, blob in content.assets.items():
            try:
                self.put_asset(blob, name=content.asset_names.get(sha, ""))
            except AssetError as exc:
                raise PackageError(f"Recurso {sha[:8]}… inválido: {exc}") from exc
        warnings = [f"Recurso ausente no pacote: {sha[:8]}…" for sha in content.missing_assets]
        payload = DraftPayload(
            schema_version=2, warnings=warnings,
            questions_v2=[q.model_dump(mode="json") for q in content.questions], cases_v2=content.cases,
        )  # fmt: skip
        return self._insert_batch(filename, "gotcha", content.title or filename, payload)

    # --- exames e questões ----------------------------------------------------------------------------------
    def list_exams(self) -> list[ExamInfo]:
        exams = []
        for row in self.db.query("SELECT id, name FROM exams ORDER BY created_at"):
            topics = [
                r["topic"]
                for r in self.db.query(
                    "SELECT DISTINCT topic FROM questions WHERE exam_id = ? ORDER BY topic",
                    (row["id"],),
                )
            ]
            count = self.db.one("SELECT COUNT(*) AS n FROM questions WHERE exam_id = ?", (row["id"],))
            exams.append(
                ExamInfo(
                    id=row["id"],
                    name=row["name"],
                    question_count=count["n"] if count else 0,
                    topics=topics,
                )
            )
        return exams

    def rename_exam(self, exam_id: str, name: str) -> None:
        self.db.execute("UPDATE exams SET name = ? WHERE id = ?", (name.strip(), exam_id))

    def delete_exam(self, exam_id: str) -> None:
        with self.db.transaction():
            for r in self.db.query("SELECT id FROM questions WHERE exam_id = ?", (exam_id,)):
                self.db.execute("DELETE FROM asset_refs WHERE owner = ?", (r["id"],))
                self.db.execute("DELETE FROM question_stats WHERE question_id = ?", (r["id"],))
            for r in self.db.query("SELECT id FROM cases WHERE exam_id = ?", (exam_id,)):
                self.db.execute("DELETE FROM asset_refs WHERE owner = ?", (r["id"],))
            self.db.execute("DELETE FROM questions WHERE exam_id = ?", (exam_id,))
            self.db.execute("DELETE FROM cases WHERE exam_id = ?", (exam_id,))
            self.db.execute("DELETE FROM exams WHERE id = ?", (exam_id,))

    def questions(self, exam_ids: Sequence[str]) -> list[QuestionBase]:
        if not exam_ids:
            return []
        marks = ",".join("?" * len(exam_ids))
        rows = self.db.query(
            f"SELECT data, exam_id, batch_id FROM questions WHERE exam_id IN ({marks})"
            " ORDER BY exam_id, topic, number",
            list(exam_ids),
        )
        out = []
        for r in rows:
            q = load_question(r["data"])
            out.append(q.model_copy(update={"exam_id": r["exam_id"], "batch_id": r["batch_id"]}))
        return out

    def get_question(self, question_id: str) -> QuestionBase:
        row = self.db.one("SELECT data, exam_id, batch_id FROM questions WHERE id = ?", (question_id,))
        if row is None:
            raise KeyError(question_id)
        q = load_question(row["data"])
        return q.model_copy(update={"exam_id": row["exam_id"], "batch_id": row["batch_id"]})
