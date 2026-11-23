"""Fábrica de questões de exemplo (uma por tipo) com respostas certas e erradas."""

from __future__ import annotations

from typing import Any

from gotcha.qtypes import (
    ActiveScreen,
    BuildList,
    DragDrop,
    HotArea,
    Lab,
    MultipleChoice,
    MultipleSelect,
    SelfAssessed,
    parse_question,
)
from gotcha.qtypes.base import Question

SHA = "a" * 64


def para(text: str) -> dict[str, Any]:
    return {"type": "paragraph", "text": text}


def opt(i: str, text: str) -> dict[str, Any]:
    return {"id": i, "blocks": [para(text)]}


SCREEN: dict[str, Any] = {
    "start": "s1",
    "state": {
        "ip": {"type": "string", "initial": ""},
        "applied": {"type": "bool", "initial": False},
    },
    "screens": [
        {
            "id": "s1",
            "title": "Rede",
            "components": [
                {"id": "ip", "type": "input", "label": "Endereço IP", "bind": "ip"},
                {
                    "id": "go",
                    "type": "button",
                    "label": "Aplicar",
                    "on_click": [{"do": "set", "var": "applied", "value": True}],
                },
            ],
        }
    ],
}
CHECKS = [
    {"id": "c1", "label": "IP correto", "when": {"==": [{"var": "ip"}, "10.0.0.5"]}, "points": 1},
    {"id": "c2", "label": "Aplicado", "when": {"==": [{"var": "applied"}, True]}, "points": 1},
]
COMPLETION = {"and": [c["when"] for c in CHECKS]}
EV_OK = [
    {"component": "ip", "type": "change", "value": "10.0.0.5"},
    {"component": "go", "type": "click"},
]
EV_BAD = [
    {"component": "ip", "type": "change", "value": "1.1.1.1"},
    {"component": "go", "type": "click"},
]

RAW: dict[str, dict[str, Any]] = {
    "multiple_choice": {
        "type": "multiple_choice",
        "number": 1,
        "prompt": [para("Qual?")],
        "options": [opt("a", "um"), opt("b", "dois"), opt("c", "tres")],
        "correct": "b",
    },
    "multiple_select": {
        "type": "multiple_select",
        "number": 2,
        "prompt": [para("Quais?")],
        "options": [opt("a", "um"), opt("b", "dois"), opt("c", "tres"), opt("d", "quatro")],
        "correct": ["a", "c"],
    },
    "build_list": {
        "type": "build_list",
        "number": 3,
        "prompt": [para("Ordene")],
        "pool": [opt("p1", "um"), opt("p2", "dois"), opt("p3", "tres"), opt("p4", "isca")],
        "answer_sequence": ["p3", "p1", "p2"],
    },
    "drag_drop": {
        "type": "drag_drop",
        "number": 4,
        "prompt": [para("Associe")],
        "items": [
            {"id": "i1", "blocks": [para("A")]},
            {"id": "i2", "blocks": [para("B")]},
            {"id": "i3", "blocks": [para("C")]},
        ],
        "targets": [
            {"id": "t1", "blocks": [para("X")], "max_items": 1},
            {"id": "t2", "blocks": [para("Y")], "max_items": 2},
        ],
        "key": {"t1": ["i1"], "t2": ["i2", "i3"]},
    },
    "hot_area": {
        "type": "hot_area",
        "number": 5,
        "prompt": [para("Clique")],
        "image": {"type": "image", "asset": SHA, "alt": "diagrama"},
        "aspect": 0.5,
        "shapes": [
            {
                "id": "s1",
                "label": "caixa",
                "geometry": {"kind": "rect", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2},
            },
            {
                "id": "s2",
                "label": "círculo",
                "geometry": {"kind": "circle", "cx": 0.6, "cy": 0.5, "r": 0.1},
            },
            {
                "id": "s3",
                "label": "poly",
                "geometry": {"kind": "polygon", "points": [[0.7, 0.1], [0.9, 0.1], [0.8, 0.3]]},
            },
        ],
        "correct": ["s2"],
    },
    "active_screen": {
        "type": "active_screen",
        "number": 6,
        "prompt": [para("Configure")],
        "screen": SCREEN,
        "checks": CHECKS,
        "completion": COMPLETION,
        "fidelity": "reconstructed",
        "limitations": ["Visual simplificado."],
    },
    "lab_simulated": {
        "type": "lab",
        "number": 7,
        "prompt": [para("Laboratório")],
        "mode": "simulated",
        "objectives": ["Configurar o IP"],
        "environment": {"kind": "local-simulation", "description": "Simulação local"},
        "steps": [{"id": "st1", "title": "IP", "instructions": [para("Defina o IP")]}],
        "screen": SCREEN,
        "checks": CHECKS,
        "completion": COMPLETION,
    },
    "lab_external": {
        "type": "lab",
        "number": 8,
        "prompt": [para("Laboratório externo")],
        "mode": "external_instructions",
        "objectives": ["Criar a VM"],
        "environment": {"kind": "external", "description": "Sua própria máquina virtual"},
        "steps": [
            {"id": "e1", "title": "Criar", "instructions": [para("Crie")]},
            {"id": "e2", "title": "Testar", "instructions": [para("Teste")]},
        ],
    },
    "self_assessed": {
        "type": "self_assessed",
        "number": 9,
        "prompt": [para("Descreva")],
        "answer_blocks": [para("Resposta de referência")],
    },
}
CORRECT: dict[str, dict[str, Any]] = {
    "multiple_choice": {"selected": ["b"]},
    "multiple_select": {"selected": ["c", "a"]},
    "build_list": {"sequence": ["p3", "p1", "p2"]},
    "drag_drop": {"placements": {"t1": ["i1"], "t2": ["i3", "i2"]}},
    "hot_area": {"selected": ["s2"]},
    "active_screen": {"events": EV_OK},
    "lab_simulated": {"events": EV_OK},
    "lab_external": {"attested": ["e1", "e2"]},
    "self_assessed": {"self_mark": True},
}
WRONG: dict[str, dict[str, Any]] = {
    "multiple_choice": {"selected": ["a"]},
    "multiple_select": {"selected": ["a"]},
    "build_list": {"sequence": ["p1", "p2", "p3"]},
    "drag_drop": {"placements": {"t1": ["i2"], "t2": ["i1", "i3"]}},
    "hot_area": {"selected": ["s1"]},
    "active_screen": {"events": EV_BAD},
    "lab_simulated": {"events": EV_BAD},
    "lab_external": {"attested": ["e1"]},
    "self_assessed": {"self_mark": False},
}
# campos que NUNCA podem aparecer na visão pública (modo prova)
HIDDEN: dict[str, set[str]] = {
    "multiple_choice": {"correct"},
    "multiple_select": {"correct"},
    "build_list": {"answer_sequence"},
    "drag_drop": {"key"},
    "hot_area": {"correct"},
    "active_screen": {"completion", "checks"},
    "lab_simulated": {"completion", "checks"},
    "lab_external": set(),
    "self_assessed": {"answer_blocks"},
}
# alterações que quebram a coerência interna (devem ser apontadas pelo validador)
BROKEN: dict[str, dict[str, Any]] = {
    "multiple_choice": {"correct": "zzz"},
    "multiple_select": {"correct": ["a", "zzz"]},
    "build_list": {"answer_sequence": ["p3", "nao-existe"]},
    "drag_drop": {"key": {"t1": ["i1"], "tX": ["i2"]}},
    "hot_area": {"correct": ["nao-existe"]},
    "active_screen": {"completion": {"eval": ["1"]}},
    "lab_simulated": {"completion": {"eval": ["1"]}},
    "lab_external": {"steps": []},
    "self_assessed": {"answer_blocks": []},
}


def make(name: str, **overrides: Any) -> Question:
    return parse_question({**RAW[name], **overrides})


ALL = list(RAW)
__all__ = [
    "ALL",
    "BROKEN",
    "CORRECT",
    "HIDDEN",
    "WRONG",
    "ActiveScreen",
    "BuildList",
    "DragDrop",
    "HotArea",
    "Lab",
    "MultipleChoice",
    "MultipleSelect",
    "SelfAssessed",
    "make",
]  # fmt: skip
