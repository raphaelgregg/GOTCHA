"""Modelos iniciais válidos por tipo, usados para criar e converter questões no editor."""

from __future__ import annotations

from typing import Any

from .base import REGISTRY

_TEXT = {"type": "paragraph", "text": ""}


def _opt(i: str, text: str) -> dict[str, Any]:
    return {"id": i, "blocks": [{"type": "paragraph", "text": text}]}


_SCREEN: dict[str, Any] = {
    "start": "tela1",
    "state": {"nome": {"type": "string", "initial": ""}, "salvo": {"type": "bool", "initial": False}},
    "screens": [
        {
            "id": "tela1",
            "title": "Configuração",
            "components": [
                {"id": "nome", "type": "input", "label": "Nome", "bind": "nome"},
                {
                    "id": "salvar",
                    "type": "button",
                    "label": "Salvar",
                    "on_click": [{"do": "set", "var": "salvo", "value": True}],
                },
            ],
        }
    ],
}
_CHECKS = [
    {"id": "nome-ok", "label": "Nome informado", "when": {"!=": [{"var": "nome"}, ""]}, "points": 1},
    {"id": "salvo-ok", "label": "Configuração salva", "when": {"==": [{"var": "salvo"}, True]}, "points": 1},
]
_COMPLETION: dict[str, Any] = {"and": [c["when"] for c in _CHECKS]}


def template(type_: str, mode: str = "simulated") -> dict[str, Any]:
    """Esqueleto válido do tipo (sem identidade, posição nem enunciado)."""
    if type_ not in REGISTRY:
        raise ValueError(f"Tipo de questão desconhecido: {type_!r}.")
    t: dict[str, Any]
    if type_ == "multiple_choice":
        t = {"options": [_opt("A", "Alternativa A"), _opt("B", "Alternativa B")], "correct": "A"}
    elif type_ == "multiple_select":
        t = {
            "options": [_opt("A", "Alternativa A"), _opt("B", "Alternativa B"), _opt("C", "Alternativa C")],
            "correct": ["A", "B"],
        }
    elif type_ == "build_list":
        t = {
            "pool": [_opt("p1", "Primeiro"), _opt("p2", "Segundo"), _opt("p3", "Item extra")],
            "answer_sequence": ["p1", "p2"],
        }
    elif type_ == "drag_drop":
        t = {
            "items": [
                {"id": "i1", "blocks": [{"type": "paragraph", "text": "Item 1"}]},
                {"id": "i2", "blocks": [{"type": "paragraph", "text": "Item 2"}]},
            ],
            "targets": [
                {"id": "t1", "blocks": [{"type": "paragraph", "text": "Destino 1"}], "max_items": 1},
                {"id": "t2", "blocks": [{"type": "paragraph", "text": "Destino 2"}], "max_items": 1},
            ],
            "key": {"t1": ["i1"], "t2": ["i2"]},
        }
    elif type_ == "hot_area":
        t = {
            "image": {"type": "image", "asset": None, "name": "adicione-uma-imagem", "alt": ""},
            "aspect": 0.5,
            "shapes": [
                {
                    "id": "r1",
                    "label": "Região 1",
                    "geometry": {"kind": "rect", "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3},
                }
            ],
            "correct": ["r1"],
        }
    elif type_ == "active_screen":
        t = {
            "screen": _SCREEN,
            "checks": _CHECKS,
            "completion": _COMPLETION,
            "fidelity": "reconstructed",
            "limitations": [],
        }
    elif type_ == "lab":
        t = {
            "mode": mode,
            "objectives": ["Descreva o objetivo"],
            "environment": {
                "kind": "local-simulation" if mode == "simulated" else "external",
                "description": "",
            },
            "steps": [
                {
                    "id": "etapa1",
                    "title": "Etapa 1",
                    "instructions": [{"type": "paragraph", "text": "Descreva a etapa."}],
                }
            ],
        }
        if mode == "simulated":
            t.update({"screen": _SCREEN, "checks": _CHECKS, "completion": _COMPLETION})
    else:  # self_assessed
        t = {"answer_blocks": [{"type": "paragraph", "text": "Resposta de referência"}]}
    return {"type": type_, "prompt": [dict(_TEXT)], **t}


def convert(question: dict[str, Any], to: str, mode: str = "simulated") -> dict[str, Any]:
    """Troca o tipo preservando identidade, posição, enunciado, explicação, estudo de caso e conversão."""
    keep = (
        "uid",
        "exam_id",
        "topic",
        "number",
        "prompt",
        "explanation",
        "case_id",
        "scoring",
        "source",
        "conversion",
        "tags",
    )
    base = {k: question[k] for k in keep if k in question}
    skeleton = template(to, mode)
    skeleton.pop("prompt")
    return {**skeleton, **base, "type": to}
