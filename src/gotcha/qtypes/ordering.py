"""Build List: organizar elementos em sequência."""

from __future__ import annotations

import random
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import QuestionBase, TypeSpec, grade_from_score, register
from .blocks import Block


class Item(BaseModel):
    id: str
    blocks: list[Block] = Field(default_factory=list)


class OrderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: list[str] = Field(default_factory=list, max_length=100)


class BuildList(QuestionBase):
    type: Literal["build_list"] = "build_list"
    pool: list[Item] = Field(max_length=100)  # inclui distratores
    answer_sequence: list[str]
    feedback: str = ""


def _validate(q: BuildList) -> list[str]:
    ids = [i.id for i in q.pool]
    errors = []
    if len(set(ids)) != len(ids):
        errors.append("Há itens com identificador repetido.")
    if not q.answer_sequence:
        errors.append("A sequência correta está vazia.")
    if len(set(q.answer_sequence)) != len(q.answer_sequence):
        errors.append("A sequência correta repete itens.")
    if not set(q.answer_sequence) <= set(ids):
        errors.append("A sequência cita itens que não existem.")
    return errors


def _grade(q: BuildList, r: OrderResponse):  # type: ignore[no-untyped-def]
    want = q.answer_sequence
    if r.sequence == want:
        return grade_from_score(1.0, q.scoring.partial)
    hits = sum(1 for i, item in enumerate(want) if i < len(r.sequence) and r.sequence[i] == item)
    return grade_from_score(hits / len(want), q.scoring.partial)


def _public(q: BuildList, seed: int) -> dict[str, object]:
    pool = [i.model_dump(mode="json") for i in q.pool]
    random.Random(f"{seed}:{q.uid}").shuffle(pool)  # embaralhamento reproduzível por sessão
    return {"pool": pool, "answer_length": len(q.answer_sequence)}


register(
    TypeSpec(
        name="build_list",
        model=BuildList,
        response=OrderResponse,
        grade=_grade,
        public=_public,
        key=lambda q: {"answer_sequence": list(q.answer_sequence)},
        validate=_validate,
        answered=lambda r: bool(r.sequence),
        interactive=True,
    )
)
