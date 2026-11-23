"""Rotas do gerador de simulado e da prova."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from gotcha.domain.builder import SimuladoSpec
from gotcha.domain.exposure import public_view
from gotcha.domain.grading import Response
from gotcha.storage.sessions import Result, SessionRow

from .services import Services, services

router = APIRouter(prefix="/api")


class ResponseBody(BaseModel):
    selected: list[str] = []
    self_mark: bool | None = None


class MarkBody(BaseModel):
    marked: bool


def _cases(svc: Services, question_cases: list[str | None]) -> dict[str, Any]:
    return {
        cid: svc.library.get_case(cid).model_dump(mode="json")
        for cid in sorted({c for c in question_cases if c})
    }


def _state(svc: Services, s: SessionRow) -> dict[str, Any]:
    reveal = s.finished_at is not None
    questions = [svc.library.get_question(qid) for qid in s.question_ids]
    return {
        "id": s.id,
        "mode": s.spec.mode,
        "finished": reveal,
        "remaining_seconds": svc.sessions.remaining_seconds(s.id),
        "time_limit_seconds": s.limit_seconds,
        "elapsed_seconds": int(svc.sessions.elapsed(s)),
        "paused": s.resumed_at is None and not reveal,
        "questions": [public_view(q, reveal) for q in questions],
        "responses": {
            k: {"selected": v.selected, "self_mark": v.self_mark} for k, v in s.responses.items()
        },
        "marks": sorted(s.marks),
        "cases": _cases(svc, [q.case_id for q in questions]),
    }


def _result(svc: Services, session_id: str, result: Result) -> dict[str, Any]:
    details = []
    for d in result.details:
        q = svc.library.get_question(d.question_id)
        details.append({**public_view(q, reveal=True), **d.model_dump(mode="json")})
    for item in details:  # `id` da questão e `question_id` do detalhe coincidem
        item["id"] = item["question_id"]
    s = result.summary
    return {
        "session_id": session_id,
        "summary": {**s.__dict__, "auto_pct": s.auto_pct, "self_pct": s.self_pct},
        "duration_seconds": result.duration_seconds,
        "details": details,
        "cases": _cases(svc, [d["case_id"] for d in details]),
    }


@router.post("/simulados")
def create_simulado(request: Request, spec: SimuladoSpec) -> dict[str, str]:
    return {"session_id": services(request).sessions.create(spec).id}


@router.get("/sessions")
def list_sessions(request: Request) -> list[dict[str, object]]:
    return services(request).sessions.list_sessions()


@router.get("/sessions/{session_id}")
def get_session(request: Request, session_id: str) -> dict[str, Any]:
    svc = services(request)
    return _state(svc, svc.sessions.get(session_id))


@router.put("/sessions/{session_id}/responses/{question_id}")
def answer(
    request: Request, session_id: str, question_id: str, body: ResponseBody
) -> dict[str, str]:
    services(request).sessions.answer(
        session_id, question_id, Response(selected=body.selected, self_mark=body.self_mark)
    )
    return {"status": "ok"}


@router.put("/sessions/{session_id}/marks/{question_id}")
def mark(request: Request, session_id: str, question_id: str, body: MarkBody) -> dict[str, str]:
    services(request).sessions.mark(session_id, question_id, body.marked)
    return {"status": "ok"}


@router.post("/sessions/{session_id}/pause")
def pause(request: Request, session_id: str) -> dict[str, str]:
    services(request).sessions.pause(session_id)
    return {"status": "ok"}


@router.post("/sessions/{session_id}/resume")
def resume(request: Request, session_id: str) -> dict[str, str]:
    services(request).sessions.resume(session_id)
    return {"status": "ok"}


@router.post("/sessions/{session_id}/finish")
def finish(request: Request, session_id: str) -> dict[str, Any]:
    svc = services(request)
    return _result(svc, session_id, svc.sessions.finish(session_id))


@router.get("/sessions/{session_id}/result")
def result(request: Request, session_id: str) -> dict[str, Any]:
    svc = services(request)
    res = svc.sessions.result_of(session_id)
    if res is None:
        raise HTTPException(409, "A prova ainda não foi encerrada.")
    return _result(svc, session_id, res)


@router.get("/sessions/{session_id}/solution/{question_id}")
def solution(request: Request, session_id: str, question_id: str) -> dict[str, Any]:
    svc = services(request)
    s = svc.sessions.get(session_id)
    if s.spec.mode != "study" and s.finished_at is None:
        raise HTTPException(
            403, "O gabarito só aparece no modo estudo ou depois de encerrar a prova."
        )
    if question_id not in s.question_ids:
        raise HTTPException(404, "Questão não faz parte desta prova.")
    return public_view(svc.library.get_question(question_id), reveal=True)
