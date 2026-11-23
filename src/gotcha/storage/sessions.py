"""Sessões de prova: o backend é a fonte do tempo, das respostas e da correção."""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from gotcha.domain.builder import History, SimuladoSpec, build
from gotcha.domain.grading import Outcome, Response, Summary, grade, summarize

from .db import Database
from .library import Library


class TimeExpired(RuntimeError):
    pass


class SessionFinished(RuntimeError):
    pass


class Detail(BaseModel):
    question_id: str
    outcome: Outcome
    selected: list[str] = []
    self_mark: bool | None = None


@dataclass
class Result:
    summary: Summary
    details: list[Detail]
    duration_seconds: int


@dataclass
class SessionRow:
    id: str
    spec: SimuladoSpec
    created_at: float
    finished_at: float | None
    question_ids: list[str]
    responses: dict[str, Response]
    marks: set[str]
    elapsed_before: float
    resumed_at: float | None
    limit_seconds: int | None


def _response_from(d: dict[str, object]) -> Response:
    return Response(selected=list(d.get("selected", [])), self_mark=d.get("self_mark"))  # type: ignore[call-overload,arg-type]


class Sessions:
    def __init__(
        self, db: Database, library: Library, clock: Callable[[], float] = time.time
    ) -> None:
        self.db = db
        self.library = library
        self.clock = clock

    # --- criação e leitura -------------------------------------------------------------------
    def create(self, spec: SimuladoSpec) -> SessionRow:
        bank = self.library.questions(spec.exam_ids)
        chosen = build(bank, spec, self.history(spec.exam_ids))
        if not chosen:
            raise ValueError("O simulado ficaria vazio: nenhuma questão corresponde aos filtros.")
        now = self.clock()
        limit = spec.time_limit_minutes * 60 if spec.time_limit_minutes else None
        sid = uuid.uuid4().hex[:12]
        self.db.execute(
            "INSERT INTO sessions (id, spec, created_at, question_ids, responses, marks,"
            " elapsed_before, resumed_at, limit_seconds) VALUES (?, ?, ?, ?, '{}', '[]', 0, ?, ?)",
            (sid, spec.model_dump_json(), now, json.dumps([q.id for q in chosen]), now, limit),
        )
        return self.get(sid)

    def get(self, session_id: str) -> SessionRow:
        row = self.db.one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if row is None:
            raise KeyError(session_id)
        return SessionRow(
            id=row["id"], spec=SimuladoSpec.model_validate_json(row["spec"]),
            created_at=row["created_at"], finished_at=row["finished_at"],
            question_ids=json.loads(row["question_ids"]),
            responses={k: _response_from(v) for k, v in json.loads(row["responses"]).items()},
            marks=set(json.loads(row["marks"])), elapsed_before=row["elapsed_before"],
            resumed_at=row["resumed_at"], limit_seconds=row["limit_seconds"],
        )  # fmt: skip

    def result_of(self, session_id: str) -> Result | None:
        row = self.db.one("SELECT result FROM sessions WHERE id = ?", (session_id,))
        if row is None or row["result"] is None:
            return None
        data = json.loads(row["result"])
        return Result(
            summary=Summary(**data["summary"]),
            details=[Detail.model_validate(d) for d in data["details"]],
            duration_seconds=data["duration_seconds"],
        )

    def list_sessions(self) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for row in self.db.query("SELECT id FROM sessions ORDER BY created_at DESC"):
            s = self.get(row["id"])
            result = self.result_of(s.id)
            out.append(
                {
                    "id": s.id, "mode": s.spec.mode, "created_at": s.created_at,
                    "finished_at": s.finished_at, "question_count": len(s.question_ids),
                    "auto_pct": result.summary.auto_pct if result else None,
                    "self_pct": result.summary.self_pct if result else None,
                }
            )  # fmt: skip
        return out

    # --- tempo -----------------------------------------------------------------------------------
    def elapsed(self, s: SessionRow) -> float:
        running = (self.clock() - s.resumed_at) if s.resumed_at is not None else 0.0
        return s.elapsed_before + running

    def remaining_seconds(self, session_id: str) -> int | None:
        s = self.get(session_id)
        if s.limit_seconds is None:
            return None
        return max(0, int(s.limit_seconds - self.elapsed(s)))

    def pause(self, session_id: str) -> None:
        s = self.get(session_id)
        if s.resumed_at is None or s.finished_at is not None:
            return
        self.db.execute(
            "UPDATE sessions SET elapsed_before = ?, resumed_at = NULL WHERE id = ?",
            (self.elapsed(s), session_id),
        )

    def resume(self, session_id: str) -> None:
        s = self.get(session_id)
        if s.resumed_at is None and s.finished_at is None:
            self.db.execute(
                "UPDATE sessions SET resumed_at = ? WHERE id = ?", (self.clock(), session_id)
            )

    # --- respostas -------------------------------------------------------------------------------
    def _open(self, session_id: str) -> SessionRow:
        s = self.get(session_id)
        if s.finished_at is not None:
            raise SessionFinished("A prova já foi encerrada.")
        remaining = self.remaining_seconds(session_id)
        if remaining is not None and remaining <= 0:
            raise TimeExpired("O tempo da prova acabou.")
        return s

    def answer(self, session_id: str, question_id: str, response: Response) -> None:
        s = self._open(session_id)
        if question_id not in s.question_ids:
            raise KeyError(question_id)
        s.responses[question_id] = response
        payload = {
            k: {"selected": v.selected, "self_mark": v.self_mark} for k, v in s.responses.items()
        }
        self.db.execute(
            "UPDATE sessions SET responses = ? WHERE id = ?", (json.dumps(payload), session_id)
        )

    def mark(self, session_id: str, question_id: str, marked: bool) -> None:
        s = self.get(session_id)
        if s.finished_at is not None:
            raise SessionFinished("A prova já foi encerrada.")
        if question_id not in s.question_ids:
            raise KeyError(question_id)
        (s.marks.add if marked else s.marks.discard)(question_id)
        self.db.execute(
            "UPDATE sessions SET marks = ? WHERE id = ?", (json.dumps(sorted(s.marks)), session_id)
        )

    # --- encerramento --------------------------------------------------------------------------
    def finish(self, session_id: str) -> Result:
        s = self.get(session_id)
        existing = self.result_of(session_id)
        if existing is not None:
            return existing
        details: list[Detail] = []
        for qid in s.question_ids:
            response = s.responses.get(qid, Response())
            outcome = grade(self.library.get_question(qid), response)
            details.append(
                Detail(
                    question_id=qid,
                    outcome=outcome,
                    selected=response.selected,
                    self_mark=response.self_mark,
                )
            )
        summary = summarize(d.outcome for d in details)
        duration = int(self.elapsed(s))
        now = self.clock()
        result_json = json.dumps(
            {
                "summary": summary.__dict__,
                "details": [d.model_dump(mode="json") for d in details],
                "duration_seconds": duration,
            }
        )
        with self.db.transaction():
            self.db.execute(
                "UPDATE sessions SET finished_at = ?, elapsed_before = ?, resumed_at = NULL,"
                " result = ? WHERE id = ?",
                (now, duration, result_json, session_id),
            )
            for d in details:
                self.db.execute(
                    "INSERT INTO question_stats (question_id, last_outcome, marked)"
                    " VALUES (?, ?, ?)"
                    " ON CONFLICT(question_id) DO UPDATE SET"
                    " last_outcome = COALESCE(excluded.last_outcome, last_outcome),"
                    " marked = excluded.marked",
                    (
                        d.question_id,
                        None if d.outcome is Outcome.UNANSWERED else d.outcome.value,
                        1 if d.question_id in s.marks else 0,
                    ),
                )
        return Result(summary=summary, details=details, duration_seconds=duration)

    def history(self, exam_ids: list[str]) -> History:
        history = History()
        if not exam_ids:
            return history
        marks = ",".join("?" * len(exam_ids))
        rows = self.db.query(
            "SELECT st.question_id, st.last_outcome, st.marked FROM question_stats st"
            f" JOIN questions q ON q.id = st.question_id WHERE q.exam_id IN ({marks})",
            exam_ids,
        )
        for r in rows:
            if r["last_outcome"]:
                history.last_outcome[r["question_id"]] = Outcome(r["last_outcome"])
            if r["marked"]:
                history.marked.add(r["question_id"])
        return history
