"""Geometria normalizada para Hot Area e alvos de Drag and Drop.

Todas as coordenadas são relativas à imagem: `x` em [0, 1] da largura, `y` em [0, 1] da altura.
O raio do círculo é relativo à **largura**, então o círculo continua redondo em qualquer proporção;
por isso o teste de pertinência recebe `aspect = altura / largura`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, field_validator, model_validator

EPS = 1e-9


def _unit(v: float, name: str) -> float:
    if not (-EPS <= v <= 1 + EPS):
        raise ValueError(f"{name} deve estar entre 0 e 1 (recebido {v}).")
    return v


class Rect(BaseModel):
    kind: Literal["rect"] = "rect"
    x: float
    y: float
    w: float
    h: float

    @model_validator(mode="after")
    def _check(self) -> Rect:
        _unit(self.x, "x")
        _unit(self.y, "y")
        if self.w <= 0 or self.h <= 0:
            raise ValueError("Largura e altura devem ser positivas.")
        _unit(self.x + self.w, "x + w")
        _unit(self.y + self.h, "y + h")
        return self


class Circle(BaseModel):
    kind: Literal["circle"] = "circle"
    cx: float
    cy: float
    r: float

    @model_validator(mode="after")
    def _check(self) -> Circle:
        _unit(self.cx, "cx")
        _unit(self.cy, "cy")
        if not (0 < self.r <= 1):
            raise ValueError("O raio deve ser maior que 0 e no máximo 1 (relativo à largura).")
        return self


class Polygon(BaseModel):
    kind: Literal["polygon"] = "polygon"
    points: list[tuple[float, float]] = Field(min_length=3, max_length=200)

    @field_validator("points")
    @classmethod
    def _check(cls, points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        for x, y in points:
            _unit(x, "x")
            _unit(y, "y")
        return points


Shape = Annotated[Rect | Circle | Polygon, Field(discriminator="kind")]
_ADAPTER: TypeAdapter[Rect | Circle | Polygon] = TypeAdapter(Shape)


def parse_shape(data: object) -> Rect | Circle | Polygon:
    return _ADAPTER.validate_python(data)


def contains(shape: Rect | Circle | Polygon, x: float, y: float, aspect: float = 1.0) -> bool:
    if isinstance(shape, Rect):
        return shape.x <= x <= shape.x + shape.w and shape.y <= y <= shape.y + shape.h
    if isinstance(shape, Circle):
        dx = x - shape.cx
        dy = (y - shape.cy) * aspect
        return dx * dx + dy * dy <= shape.r * shape.r
    return _in_polygon(shape.points, x, y)


def _in_polygon(points: list[tuple[float, float]], x: float, y: float) -> bool:
    """Lançamento de raio (par-ímpar); o escalonamento por eixo não altera o resultado."""
    inside = False
    j = len(points) - 1
    for i, (xi, yi) in enumerate(points):
        xj, yj = points[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside
