"""Envelope comum das questões, registro de tipos e despacho de correção e exposição."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gotcha.domain.grading import Grade, Outcome

from .blocks import Block

SCHEMA_VERSION = 2


def new_uid() -> str:
    return "q_" + uuid.uuid4().hex[:20]


class Scoring(BaseModel):
    points: int = Field(default=1, ge=1, le=100)
    partial: bool = False


class Conversion(BaseModel):
    """O que foi preservado ou perdido ao converter a questão. Nada é descartado em silêncio."""

    status: Literal["ok", "partial", "manual_required"] = "ok"
    preserved: list[str] = Field(default_factory=list)
    lost: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    original_snippet: str = ""


class Source(BaseModel):
    format: str = ""
    file: str = ""
    ref: str = ""


class QuestionBase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    uid: str = Field(default_factory=new_uid)
    schema_version: int = SCHEMA_VERSION
    exam_id: str | None = None  # campos de execução: não vão para o pacote
    batch_id: str | None = None
    topic: int = 1
    number: int
    prompt: list[Block] = Field(default_factory=list)
    explanation: list[Block] = Field(default_factory=list)
    case_id: str | None = None
    scoring: Scoring = Field(default_factory=Scoring)
    source: Source = Field(default_factory=Source)
    conversion: Conversion = Field(default_factory=Conversion)
    tags: list[str] = Field(default_factory=list)

    type: str  # sobrescrito por cada tipo com Literal

    @property
    def id(self) -> str:
        return self.uid

    @property
    def position(self) -> tuple[int, int]:
        """Posição de origem (tópico, número): serve para ordenar, nunca como identidade."""
        return (self.topic, self.number)

    def fingerprint(self) -> str:
        """Hash do conteúdo (sem identidade, posição, origem nem explicação) para detectar duplicatas."""
        content = self.model_dump(
            mode="json",
            exclude={
                "uid", "schema_version", "exam_id", "batch_id", "topic", "number", "explanation",
                "source", "conversion", "tags", "case_id",
            },
        )  # fmt: skip
        canon = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


Question = QuestionBase


@dataclass(frozen=True)
class TypeSpec:
    """Tudo o que um tipo de questão fornece, registrado em um único lugar."""

    name: str
    model: type[QuestionBase]
    response: type[BaseModel]
    grade: Callable[[Any, Any], Grade]
    public: Callable[[Any, int], dict[str, Any]]
    key: Callable[[Any], dict[str, Any]]
    validate: Callable[[Any], list[str]]
    answered: Callable[[Any], bool]
    interactive: bool = False  # vira "tipo interativo" no filtro do gerador de simulado


REGISTRY: dict[str, TypeSpec] = {}


def register(spec: TypeSpec) -> TypeSpec:
    REGISTRY[spec.name] = spec
    return spec


class NoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


def parse_response(q: QuestionBase, raw: dict[str, Any]) -> BaseModel:
    """Valida a resposta do usuário conforme o tipo da questão (campos desconhecidos são recusados)."""
    try:
        return REGISTRY[q.type].response.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Resposta inválida para {q.type}: {exc.errors()[0]['msg']}") from exc


def grade_question(q: QuestionBase, raw: dict[str, Any] | None) -> Grade:
    spec = REGISTRY[q.type]
    group = group_of(q)
    if not raw:
        return Grade(0.0, Outcome.UNANSWERED, group)
    response = parse_response(q, raw)
    if not spec.answered(response):
        return Grade(0.0, Outcome.UNANSWERED, group)
    return spec.grade(q, response)


def group_of(q: QuestionBase) -> Literal["auto", "self", "lab"]:
    if q.type == "self_assessed":
        return "self"
    if q.type == "lab":
        return "self" if getattr(q, "mode", "simulated") != "simulated" else "lab"
    return "auto"


def public_view(q: QuestionBase, reveal: bool, seed: int = 0) -> dict[str, Any]:
    """Visão enviada à interface. Sem `reveal`, nunca contém o gabarito nem a explicação."""
    spec = REGISTRY[q.type]
    view: dict[str, Any] = {
        "id": q.uid,
        "type": q.type,
        "topic": q.topic,
        "number": q.number,
        "prompt": [b.model_dump(mode="json") for b in q.prompt],
        "case_id": q.case_id,
        "scoring": q.scoring.model_dump(),
        "conversion": q.conversion.model_dump(),
        "interactive": spec.interactive,
    }
    view.update(spec.public(q, seed))
    if reveal:
        view["key"] = spec.key(q)
        view["explanation"] = [b.model_dump(mode="json") for b in q.explanation]
    return view


def validate_question(q: QuestionBase) -> list[str]:
    """Erros semânticos que o Pydantic sozinho não pega (referências, gabarito, coerência)."""
    return REGISTRY[q.type].validate(q)


def partial_score(selected: set[str], correct: set[str]) -> float:
    """(acertos - erros) / total de corretas, nunca abaixo de zero."""
    if not correct:
        return 0.0
    return max(0.0, (len(selected & correct) - len(selected - correct)) / len(correct))


def grade_from_score(score: float, partial: bool, group: Literal["auto", "self", "lab"] = "auto") -> Grade:
    if score >= 1.0:
        return Grade(1.0, Outcome.CORRECT, group)
    if partial and score > 0:
        return Grade(score, Outcome.PARTIAL, group)
    return Grade(0.0, Outcome.INCORRECT, group)


def summarize_question(q: QuestionBase) -> dict[str, Any]:
    """Resumo leve para listas (revisão e biblioteca)."""
    from .blocks import ImageBlock, blocks_text

    images = [b for b in q.prompt if isinstance(b, ImageBlock)]
    return {
        "id": q.uid,
        "type": q.type,
        "topic": q.topic,
        "number": q.number,
        "text": blocks_text(q.prompt)[:240],
        "status": q.conversion.status,
        "warnings": list(q.conversion.warnings),
        "images": len(images),
        "missing_images": sum(1 for i in images if i.asset is None),
        "case_id": q.case_id,
    }
