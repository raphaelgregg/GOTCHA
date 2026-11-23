"""Drag and Drop: itens arrastáveis e alvos com capacidade."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import QuestionBase, TypeSpec, grade_from_score, register
from .blocks import Block, ImageBlock
from .geometry import Shape


class DragItem(BaseModel):
    id: str
    blocks: list[Block] = Field(default_factory=list)
    reusable: bool = False


class DropTarget(BaseModel):
    id: str
    blocks: list[Block] = Field(default_factory=list)
    min_items: int = Field(default=0, ge=0)
    max_items: int = Field(default=1, ge=1)
    region: Shape | None = None  # alvo posicionado sobre a imagem de fundo (coordenadas normalizadas)


class DragResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placements: dict[str, list[str]] = Field(default_factory=dict)


class DragDrop(QuestionBase):
    type: Literal["drag_drop"] = "drag_drop"
    items: list[DragItem] = Field(max_length=100)
    targets: list[DropTarget] = Field(max_length=100)
    background: ImageBlock | None = None
    aspect: float | None = Field(default=None, gt=0)
    ordered: bool = False  # a ordem dentro de cada alvo importa
    key: dict[str, list[str]]


def _validate(q: DragDrop) -> list[str]:
    errors: list[str] = []
    items = {i.id: i for i in q.items}
    targets = {t.id: t for t in q.targets}
    if len(items) != len(q.items) or len(targets) != len(q.targets):
        errors.append("Há itens ou alvos com identificador repetido.")
    used: dict[str, int] = {}
    for tid, placed in q.key.items():
        if tid not in targets:
            errors.append(f"O gabarito cita o alvo inexistente {tid!r}.")
            continue
        if len(placed) > targets[tid].max_items:
            errors.append(f"O alvo {tid!r} recebe mais itens que sua capacidade.")
        for iid in placed:
            if iid not in items:
                errors.append(f"O gabarito cita o item inexistente {iid!r}.")
            used[iid] = used.get(iid, 0) + 1
    for iid, n in used.items():
        if n > 1 and iid in items and not items[iid].reusable:
            errors.append(f"O item {iid!r} aparece em mais de um alvo, mas não é reutilizável.")
    if q.background is not None and any(t.region for t in q.targets) and q.aspect is None:
        errors.append("Alvos sobre imagem exigem a proporção (`aspect`) da imagem.")
    return errors


def _grade(q: DragDrop, r: DragResponse):  # type: ignore[no-untyped-def]
    correct = 0
    for tid, want in q.key.items():
        got = r.placements.get(tid, [])
        same = got == want if q.ordered else sorted(got) == sorted(want)
        correct += 1 if same else 0
    total = len(q.key) or 1
    return grade_from_score(correct / total, q.scoring.partial)


register(
    TypeSpec(
        name="drag_drop",
        model=DragDrop,
        response=DragResponse,
        grade=_grade,
        public=lambda q, _s: {
            "items": [i.model_dump(mode="json") for i in q.items],
            "targets": [t.model_dump(mode="json") for t in q.targets],
            "background": q.background.model_dump(mode="json") if q.background else None,
            "aspect": q.aspect,
            "ordered": q.ordered,
        },
        key=lambda q: {"placements": {k: list(v) for k, v in q.key.items()}},
        validate=_validate,
        answered=lambda r: any(r.placements.values()),
        interactive=True,
    )
)
