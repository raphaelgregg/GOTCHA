"""Hot Area: regiões clicáveis (retângulo, círculo, polígono) sobre uma imagem."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import QuestionBase, TypeSpec, grade_from_score, partial_score, register
from .blocks import ImageBlock
from .geometry import Shape


class HotShape(BaseModel):
    id: str
    label: str = ""
    geometry: Shape


class Selection(BaseModel):
    mode: Literal["single", "multiple"] = "single"
    required_count: int | None = Field(default=None, ge=1)


class HotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selected: list[str] = Field(default_factory=list, max_length=100)


class HotArea(QuestionBase):
    type: Literal["hot_area"] = "hot_area"
    image: ImageBlock
    aspect: float = Field(gt=0)  # altura / largura da imagem
    shapes: list[HotShape] = Field(max_length=100)
    selection: Selection = Field(default_factory=Selection)
    correct: list[str]


def _validate(q: HotArea) -> list[str]:
    ids = [s.id for s in q.shapes]
    errors = []
    if not ids:
        errors.append("Defina ao menos uma região.")
    if len(set(ids)) != len(ids):
        errors.append("Há regiões com identificador repetido.")
    if not q.correct:
        errors.append("Marque ao menos uma região correta.")
    if not set(q.correct) <= set(ids):
        errors.append("O gabarito cita regiões que não existem.")
    if q.selection.mode == "single" and len(q.correct) > 1:
        errors.append("Seleção única, mas há mais de uma região correta.")
    if q.selection.required_count is not None and q.selection.required_count != len(q.correct):
        errors.append("A quantidade exigida difere do número de regiões corretas.")
    return errors


def _grade(q: HotArea, r: HotResponse):  # type: ignore[no-untyped-def]
    got, want = set(r.selected), set(q.correct)
    return grade_from_score(1.0 if got == want else partial_score(got, want), q.scoring.partial)


register(
    TypeSpec(
        name="hot_area",
        model=HotArea,
        response=HotResponse,
        grade=_grade,
        public=lambda q, _s: {
            "image": q.image.model_dump(mode="json"),
            "aspect": q.aspect,
            "shapes": [s.model_dump(mode="json") for s in q.shapes],
            "selection": {
                "mode": q.selection.mode,
                "required_count": q.selection.required_count or len(q.correct),
            },
        },
        key=lambda q: {"correct": list(q.correct)},
        validate=_validate,
        answered=lambda r: bool(r.selected),
        interactive=True,
    )
)
