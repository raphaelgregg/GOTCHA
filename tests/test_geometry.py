"""Geometria normalizada do Hot Area: independente da resolução da imagem."""

import pytest
from pydantic import ValidationError

from gotcha.qtypes.geometry import Circle, Polygon, Rect, contains, parse_shape


def test_rect_contains_points_inside_and_on_edge() -> None:
    r = Rect(kind="rect", x=0.1, y=0.2, w=0.3, h=0.2)
    assert contains(r, 0.2, 0.3) and contains(r, 0.1, 0.2) and contains(r, 0.4, 0.4)
    assert not contains(r, 0.5, 0.3) and not contains(r, 0.2, 0.5)


def test_circle_respects_image_aspect() -> None:
    # raio relativo à LARGURA; em imagem mais alta (aspect=2) o círculo continua redondo
    c = Circle(kind="circle", cx=0.5, cy=0.5, r=0.1)
    assert contains(c, 0.55, 0.5, aspect=1.0)
    assert contains(c, 0.5, 0.55, aspect=1.0)
    assert not contains(c, 0.5, 0.56, aspect=2.0)  # 0.06 de altura = 0.12 de largura (fora)
    assert contains(c, 0.5, 0.54, aspect=2.0)  # 0.04 de altura = 0.08 de largura (dentro)


def test_polygon_ray_casting_concave() -> None:
    poly = Polygon(kind="polygon", points=[(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.5, 0.5), (0.1, 0.9)])
    assert contains(poly, 0.2, 0.2)
    assert not contains(poly, 0.5, 0.8)  # dentro do recorte côncavo
    assert not contains(poly, 0.95, 0.5)


@pytest.mark.parametrize(
    "bad",
    [
        {"kind": "rect", "x": -0.1, "y": 0, "w": 0.2, "h": 0.2},
        {"kind": "rect", "x": 0.9, "y": 0, "w": 0.2, "h": 0.2},
        {"kind": "rect", "x": 0, "y": 0, "w": 0, "h": 0.2},
        {"kind": "circle", "cx": 0.5, "cy": 0.5, "r": 0},
        {"kind": "circle", "cx": 1.5, "cy": 0.5, "r": 0.1},
        {"kind": "polygon", "points": [(0, 0), (1, 1)]},
        {"kind": "polygon", "points": [(0, 0), (1, 1), (2, 0)]},
        {"kind": "star", "x": 0},
    ],
)
def test_invalid_shapes_are_rejected(bad: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises((ValidationError, ValueError)):
        parse_shape(bad)


def test_shapes_roundtrip_through_json() -> None:
    for data in (
        {"kind": "rect", "x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5},
        {"kind": "circle", "cx": 0.5, "cy": 0.5, "r": 0.25},
        {"kind": "polygon", "points": [[0.1, 0.1], [0.8, 0.2], [0.5, 0.9]]},
    ):
        shape = parse_shape(data)
        assert parse_shape(shape.model_dump(mode="json")) == shape
