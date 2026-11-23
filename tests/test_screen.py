"""Motor declarativo do Active Screen: a mesma lógica roda no servidor e no navegador."""

import json
from pathlib import Path
from typing import Any

import pytest

from gotcha.qtypes.screen import MAX_EVENTS, ScreenSpec, replay, validate_screen

VECTORS = json.loads((Path(__file__).parent / "vectors" / "screen.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", VECTORS, ids=[c["name"] for c in VECTORS])
def test_shared_vectors(case: dict) -> None:  # type: ignore[type-arg]
    spec = ScreenSpec.model_validate(case["spec"])
    assert validate_screen(spec) == []
    run = replay(spec, case["events"])
    expect = case["expect"]
    assert run.state == expect["state"]
    assert run.screen == expect["screen"]
    assert run.ignored == expect["ignored"]
    if "messages" in expect:
        assert run.messages == expect["messages"]


def spec_with(**patch: object) -> dict[str, Any]:
    base: dict[str, Any] = json.loads(json.dumps(VECTORS[0]["spec"]))
    base.update(patch)
    return base


def test_validator_points_out_broken_references() -> None:
    bad_goto = spec_with()
    bad_goto["screens"][0]["components"][0]["on_click"] = [{"do": "goto", "screen": "nope"}]
    assert any("nope" in e for e in validate_screen(ScreenSpec.model_validate(bad_goto)))
    bad_var = spec_with()
    bad_var["screens"][0]["components"][0]["on_click"] = [{"do": "set", "var": "ghost", "value": 1}]
    assert any("ghost" in e for e in validate_screen(ScreenSpec.model_validate(bad_var)))
    bad_start = spec_with(start="zzz")
    assert any("zzz" in e for e in validate_screen(ScreenSpec.model_validate(bad_start)))


def test_unknown_component_types_and_actions_are_rejected_at_parse_time() -> None:
    bad = spec_with()
    bad["screens"][0]["components"][0]["type"] = "iframe"
    with pytest.raises(ValueError):
        ScreenSpec.model_validate(bad)
    bad = spec_with()
    bad["screens"][0]["components"][0]["on_click"] = [{"do": "eval", "text": "alert(1)"}]
    with pytest.raises(ValueError):
        ScreenSpec.model_validate(bad)


def test_conditions_in_components_are_validated() -> None:
    bad = spec_with()
    bad["screens"][0]["components"][0]["visible_if"] = {"eval": ["1"]}
    assert validate_screen(ScreenSpec.model_validate(bad))


def test_event_flood_is_capped() -> None:
    spec = ScreenSpec.model_validate(VECTORS[4]["spec"])
    events = [{"component": "b", "type": "click"}] * (MAX_EVENTS + 50)
    run = replay(spec, events)
    assert len(run.state["log"]) == MAX_EVENTS
    assert run.ignored == 50


def test_replay_is_deterministic() -> None:
    spec = ScreenSpec.model_validate(VECTORS[1]["spec"])
    events = VECTORS[1]["events"]
    assert replay(spec, events).state == replay(spec, events).state
