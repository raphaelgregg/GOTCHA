"""Modelos iniciais por tipo: sempre válidos, para criar ou converter questões no editor."""

import pytest

from gotcha.qtypes import REGISTRY, parse_question, validate_question
from gotcha.qtypes.templates import convert, template


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_every_template_is_a_valid_question(name: str) -> None:
    raw = {**template(name), "number": 1}
    q = parse_question(raw)
    assert q.type == name and validate_question(q) == []


def test_lab_templates_cover_every_mode() -> None:
    for mode in ("simulated", "external_instructions", "real"):
        q = parse_question({**template("lab", mode=mode), "number": 1})
        assert validate_question(q) == [] and q.mode == mode  # type: ignore[attr-defined]


def test_convert_keeps_identity_prompt_and_media() -> None:
    from tests import qfactory as f

    original = f.make("self_assessed", uid="q_fixa", topic=3, number=9, case_id="c1")
    converted = convert(original.model_dump(mode="json"), "hot_area")
    q = parse_question(converted)
    assert (q.uid, q.topic, q.number, q.case_id) == ("q_fixa", 3, 9, "c1")
    assert q.type == "hot_area" and q.prompt == original.prompt
    assert validate_question(q) == []
