"""Biblioteca: lotes de rascunho, exames, questões confirmadas, casos e imagens."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from gotcha.domain.models import CaseStudy, Choice, ParsedBatch, Question
from gotcha.domain.sanitize import clean_html
from gotcha.importers.common import infer_kind, sha256, validate_answer

from .db import Database

EDITABLE = {"topic", "number", "kind", "stem", "choices", "answer", "explanation"}
_STALE_WARNINGS = ("Sem gabarito", "O gabarito cita")


@dataclass
class BatchView:
    id: str
    filename: str
    format: str
    title: str
    status: str
    exam_id: str | None
    questions: list[Question]
    cases: list[CaseStudy]
    warnings: list[str]


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


class DraftPayload(BaseModel):
    """O que fica salvo de um lote em rascunho."""

    questions: list[Question] = Field(default_factory=list)
    cases: list[CaseStudy] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class Library:
    def __init__(self, db: Database, clock: Callable[[], float] = time.time) -> None:
        self.db = db
        self.clock = clock

    # --- imagens -----------------------------------------------------------------------------
    def put_asset(self, data: bytes) -> str:
        sha = sha256(data)
        self.db.execute("INSERT OR IGNORE INTO assets (sha, data) VALUES (?, ?)", (sha, data))
        return sha

    def get_asset(self, sha: str) -> bytes | None:
        row = self.db.one("SELECT data FROM assets WHERE sha = ?", (sha,))
        return bytes(row["data"]) if row else None

    # --- lotes (rascunhos) -------------------------------------------------------------------
    def create_batch(self, filename: str, parsed: ParsedBatch) -> BatchView:
        for data in parsed.assets.values():
            self.put_asset(data)
        batch_id = _new_id()
        payload = DraftPayload(
            questions=parsed.questions, cases=parsed.cases, warnings=parsed.warnings
        ).model_dump_json()
        self.db.execute(
            "INSERT INTO batches (id, filename, format, title, status, created_at, payload)"
            " VALUES (?, ?, ?, ?, 'draft', ?, ?)",
            (batch_id, filename, parsed.format, parsed.title or filename, self.clock(), payload),
        )
        return self.get_batch(batch_id)

    def get_batch(self, batch_id: str) -> BatchView:
        row = self.db.one("SELECT * FROM batches WHERE id = ?", (batch_id,))
        if row is None:
            raise KeyError(batch_id)
        parsed = DraftPayload.model_validate_json(row["payload"])
        return BatchView(
            id=row["id"], filename=row["filename"], format=row["format"], title=row["title"],
            status=row["status"], exam_id=row["exam_id"], questions=parsed.questions,
            cases=parsed.cases, warnings=parsed.warnings,
        )  # fmt: skip

    def list_batches(self) -> list[BatchView]:
        rows = self.db.query("SELECT id FROM batches ORDER BY created_at DESC")
        return [self.get_batch(r["id"]) for r in rows]

    def _save_draft(self, view: BatchView) -> None:
        payload = DraftPayload(
            questions=view.questions, cases=view.cases, warnings=view.warnings
        ).model_dump_json()
        self.db.execute("UPDATE batches SET payload = ? WHERE id = ?", (payload, view.id))

    def _editable(self, batch_id: str) -> BatchView:
        view = self.get_batch(batch_id)
        if view.status != "draft":
            raise ValueError("Só lotes em rascunho podem ser editados.")
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
        shifted = [
            Choice(letter=chr(ord("A") + offset + i), text=c.text) for i, c in enumerate(b.choices)
        ]
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

    def confirm_batch(
        self, batch_id: str, exam_id: str | None = None, exam_name: str | None = None
    ) -> ConfirmResult:
        view = self._editable(batch_id)
        with self.db.transaction():
            if exam_id is None:
                exam_id = _new_id()
                name = (exam_name or view.title or view.filename).strip()
                self.db.execute(
                    "INSERT INTO exams (id, name, created_at) VALUES (?, ?, ?)",
                    (exam_id, name, self.clock()),
                )
            elif self.db.one("SELECT 1 FROM exams WHERE id = ?", (exam_id,)) is None:
                raise KeyError(exam_id)
            case_ids: dict[str, str] = {}
            added = skipped = 0
            for q in view.questions:
                exists = self.db.one(
                    "SELECT 1 FROM questions WHERE exam_id = ? AND topic = ? AND number = ?",
                    (exam_id, q.topic, q.number),
                )
                if exists:
                    skipped += 1
                    continue
                case_id = None
                if q.case_id:
                    if q.case_id not in case_ids:
                        case = next((c for c in view.cases if c.id == q.case_id), None)
                        if case:
                            case_ids[q.case_id] = _new_id()
                            self.db.execute(
                                "INSERT INTO cases (id, exam_id, batch_id, title, text)"
                                " VALUES (?, ?, ?, ?, ?)",
                                (case_ids[q.case_id], exam_id, batch_id, case.title, case.text),
                            )
                    case_id = case_ids.get(q.case_id)
                qid = _new_id()
                stored = q.model_copy(
                    update={"id": qid, "exam_id": exam_id, "batch_id": batch_id, "case_id": case_id}
                )
                self.db.execute(
                    "INSERT INTO questions (id, exam_id, batch_id, topic, number, data)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (qid, exam_id, batch_id, q.topic, q.number, stored.model_dump_json()),
                )
                added += 1
            self.db.execute(
                "UPDATE batches SET status = 'confirmed', exam_id = ? WHERE id = ?",
                (exam_id, batch_id),
            )
        return ConfirmResult(exam_id=exam_id, added=added, skipped=skipped)

    def undo_batch(self, batch_id: str) -> None:
        with self.db.transaction():
            self.db.execute(
                "DELETE FROM question_stats WHERE question_id IN"
                " (SELECT id FROM questions WHERE batch_id = ?)",
                (batch_id,),
            )
            self.db.execute("DELETE FROM questions WHERE batch_id = ?", (batch_id,))
            self.db.execute("DELETE FROM cases WHERE batch_id = ?", (batch_id,))
            self.db.execute("UPDATE batches SET status = 'undone' WHERE id = ?", (batch_id,))

    def discard_batch(self, batch_id: str) -> None:
        self.db.execute("DELETE FROM batches WHERE id = ? AND status = 'draft'", (batch_id,))

    # --- exames e questões ---------------------------------------------------------------------
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
            count = self.db.one(
                "SELECT COUNT(*) AS n FROM questions WHERE exam_id = ?", (row["id"],)
            )
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
            self.db.execute(
                "DELETE FROM question_stats WHERE question_id IN"
                " (SELECT id FROM questions WHERE exam_id = ?)",
                (exam_id,),
            )
            self.db.execute("DELETE FROM questions WHERE exam_id = ?", (exam_id,))
            self.db.execute("DELETE FROM cases WHERE exam_id = ?", (exam_id,))
            self.db.execute("DELETE FROM exams WHERE id = ?", (exam_id,))

    def questions(self, exam_ids: Sequence[str]) -> list[Question]:
        if not exam_ids:
            return []
        marks = ",".join("?" * len(exam_ids))
        rows = self.db.query(
            f"SELECT data FROM questions WHERE exam_id IN ({marks})"
            " ORDER BY exam_id, topic, number",
            list(exam_ids),
        )
        return [Question.model_validate_json(r["data"]) for r in rows]

    def get_question(self, question_id: str) -> Question:
        row = self.db.one("SELECT data FROM questions WHERE id = ?", (question_id,))
        if row is None:
            raise KeyError(question_id)
        return Question.model_validate_json(row["data"])

    def get_case(self, case_id: str) -> CaseStudy:
        row = self.db.one("SELECT id, title, text FROM cases WHERE id = ?", (case_id,))
        if row is None:
            raise KeyError(case_id)
        return CaseStudy(id=row["id"], title=row["title"] or "Estudo de caso", text=row["text"])
