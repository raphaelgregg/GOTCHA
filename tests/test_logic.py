"""Condições declarativas (sintaxe JSON Logic, avaliador próprio e de lista fechada)."""

import pytest

from gotcha.qtypes.logic import LogicError, evaluate, validate


def test_basic_operators() -> None:
    data = {"ip": "10.0.0.5", "n": 3, "flag": True, "tags": ["a", "b"]}
    assert evaluate({"==": [{"var": "ip"}, "10.0.0.5"]}, data) is True
    assert evaluate({"!=": [{"var": "n"}, 4]}, data) is True
    assert evaluate({"in": ["a", {"var": "tags"}]}, data) is True
    assert evaluate({"in": ["x", {"var": "tags"}]}, data) is False
    assert evaluate({">": [{"var": "n"}, 2]}, data) is True
    assert evaluate({"<=": [{"var": "n"}, 2]}, data) is False
    assert evaluate({"!": [{"var": "flag"}]}, data) is False


def test_and_or_short_circuit_and_nesting() -> None:
    expr = {
        "and": [
            {"==": [{"var": "a"}, 1]},
            {"or": [{"==": [{"var": "b"}, 2]}, {"==": [{"var": "c"}, 3]}]},
        ]
    }
    assert evaluate(expr, {"a": 1, "b": 0, "c": 3}) is True
    assert evaluate(expr, {"a": 0, "b": 2, "c": 3}) is False


def test_equality_is_strict_between_bool_and_number() -> None:
    assert evaluate({"==": [{"var": "x"}, 1]}, {"x": True}) is False
    assert evaluate({"==": [{"var": "x"}, True]}, {"x": True}) is True


def test_missing_variable_is_none_and_dotted_paths_work() -> None:
    assert evaluate({"var": "nope"}, {}) is None
    assert evaluate({"var": "a.b"}, {"a": {"b": 7}}) == 7
    assert evaluate({"==": [{"var": "nope"}, None]}, {}) is True


@pytest.mark.parametrize(
    "bad",
    [
        {"eval": ["1+1"]},
        {"__import__": ["os"]},
        {"==": [1, 2], "!=": [1, 2]},
        {"var": 5},
        {"in": [1]},
        {"==": [1]},
    ],
)
def test_unknown_or_malformed_expressions_are_rejected(bad: dict) -> None:  # type: ignore[type-arg]
    with pytest.raises(LogicError):
        validate(bad)
    with pytest.raises(LogicError):
        evaluate(bad, {})


def test_depth_and_size_limits() -> None:
    deep: object = {"var": "x"}
    for _ in range(40):
        deep = {"!": [deep]}
    with pytest.raises(LogicError, match="profund"):
        validate(deep)
    wide = {"and": [{"==": [1, 1]}] * 400}
    with pytest.raises(LogicError, match="tamanho"):
        validate(wide)


def test_literals_pass_through() -> None:
    assert evaluate("texto", {}) == "texto"
    assert evaluate(5, {}) == 5
    assert evaluate(None, {}) is None
