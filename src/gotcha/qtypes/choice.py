"""Múltipla escolha e múltipla seleção."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import QuestionBase, TypeSpec, grade_from_score, partial_score, register
from .blocks import Block


class Option(BaseModel):
    id: str
    blocks: list[Block] = Field(default_factory=list)


class ChoiceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selected: list[str] = Field(default_factory=list, max_length=50)


class MultipleChoice(QuestionBase):
    type: Literal["multiple_choice"] = "multiple_choice"
    options: list[Option] = Field(max_length=50)
    correct: str
    variant: Literal["standard", "true_false"] = "standard"


class MultipleSelect(QuestionBase):
    type: Literal["multiple_select"] = "multiple_select"
    options: list[Option] = Field(max_length=50)
    correct: list[str]
    required_count: int | None = Field(default=None, ge=1)


def _option_errors(q: MultipleChoice | MultipleSelect) -> list[str]:
    ids = [o.id for o in q.options]
    errors = []
    if len(ids) < 2:
        errors.append("São necessárias ao menos duas alternativas.")
    if len(set(ids)) != len(ids):
        errors.append("Há alternativas com identificador repetido.")
    return errors


def _validate_mc(q: MultipleChoice) -> list[str]:
    errors = _option_errors(q)
    if q.correct not in {o.id for o in q.options}:
        errors.append("O gabarito não corresponde a nenhuma alternativa.")
    return errors


def _validate_ms(q: MultipleSelect) -> list[str]:
    errors = _option_errors(q)
    ids = {o.id for o in q.options}
    if not q.correct:
        errors.append("Informe ao menos uma alternativa correta.")
    if not set(q.correct) <= ids:
        errors.append("O gabarito cita alternativas que não existem.")
    if q.required_count is not None and q.required_count != len(q.correct):
        errors.append("A quantidade exigida difere do número de alternativas corretas.")
    return errors


def _public_options(q: MultipleChoice | MultipleSelect) -> list[dict[str, Any]]:
    return [o.model_dump(mode="json") for o in q.options]


register(
    TypeSpec(
        name="multiple_choice",
        model=MultipleChoice,
        response=ChoiceResponse,
        grade=lambda q, r: grade_from_score(1.0 if r.selected == [q.correct] else 0.0, False),
        public=lambda q, _seed: {
            "options": _public_options(q),
            "variant": q.variant,
            "required_count": 1,
        },
        key=lambda q: {"correct": q.correct},
        validate=_validate_mc,
        answered=lambda r: bool(r.selected),
    )
)

register(
    TypeSpec(
        name="multiple_select",
        model=MultipleSelect,
        response=ChoiceResponse,
        grade=lambda q, r: grade_from_score(
            1.0 if set(r.selected) == set(q.correct) else partial_score(set(r.selected), set(q.correct)),
            q.scoring.partial,
        ),
        public=lambda q, _seed: {
            "options": _public_options(q),
            "required_count": q.required_count or len(q.correct),
        },
        key=lambda q: {"correct": list(q.correct)},
        validate=_validate_ms,
        answered=lambda r: bool(r.selected),
    )
)
