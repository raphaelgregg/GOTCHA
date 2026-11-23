"""Condições declarativas com a sintaxe do JSON Logic, em um avaliador próprio e de lista fechada.

Não há `eval`, laços, funções definidas pelo usuário nem acesso a atributos: só um conjunto fixo
de operadores sobre dados JSON, com limites de profundidade e de tamanho.
"""

from __future__ import annotations

from typing import Any

MAX_DEPTH = 12
MAX_NODES = 300
_BINARY = {"==", "!=", "<", "<=", ">", ">=", "in"}
OPERATORS = {"var", "!", "and", "or"} | _BINARY


class LogicError(ValueError):
    """Expressão inválida, desconhecida ou acima dos limites."""


def _args(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def validate(expr: Any) -> None:
    count = 0

    def walk(node: Any, depth: int) -> None:
        nonlocal count
        count += 1
        if count > MAX_NODES:
            raise LogicError("Expressão acima do tamanho máximo permitido.")
        if depth > MAX_DEPTH:
            raise LogicError("Expressão muito profunda.")
        if isinstance(node, list):
            for item in node:
                walk(item, depth + 1)
            return
        if not isinstance(node, dict):
            if isinstance(node, str | int | float | bool) or node is None:
                return
            raise LogicError("Valor não permitido na expressão.")
        if len(node) != 1:
            raise LogicError("Cada operador deve ter exatamente uma chave.")
        ((op, raw),) = node.items()
        if op not in OPERATORS:
            raise LogicError(f"Operador desconhecido: {op!r}.")
        args = _args(raw)
        if op == "var":
            if not 1 <= len(args) <= 2 or not isinstance(args[0], str):
                raise LogicError("`var` exige o nome da variável como texto.")
        elif op in _BINARY and len(args) != 2:
            raise LogicError(f"`{op}` exige exatamente dois argumentos.")
        elif op == "!" and len(args) != 1:
            raise LogicError("`!` exige um argumento.")
        elif op in {"and", "or"} and not args:
            raise LogicError(f"`{op}` exige ao menos um argumento.")
        for item in args:
            walk(item, depth + 1)

    walk(expr, 0)


def _lookup(path: str, data: dict[str, Any]) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _eq(a: Any, b: Any) -> bool:
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return bool(a == b)


def _num(v: Any) -> bool:
    return isinstance(v, int | float) and not isinstance(v, bool)


def _compare(op: str, a: Any, b: Any) -> bool:
    if not ((_num(a) and _num(b)) or (isinstance(a, str) and isinstance(b, str))):
        return False
    return bool({"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op])


def evaluate(expr: Any, data: dict[str, Any]) -> Any:
    validate(expr)
    return _eval(expr, data)


def _eval(node: Any, data: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_eval(item, data) for item in node]
    if not isinstance(node, dict):
        return node
    ((op, raw),) = node.items()
    args = _args(raw)
    if op == "var":
        found = _lookup(args[0], data)
        return found if found is not None or len(args) == 1 else _eval(args[1], data)
    if op == "and":
        result: Any = True
        for item in args:
            result = _eval(item, data)
            if not result:
                return result
        return result
    if op == "or":
        result = False
        for item in args:
            result = _eval(item, data)
            if result:
                return result
        return result
    values = [_eval(item, data) for item in args]
    if op == "!":
        return not values[0]
    a, b = values
    if op == "==":
        return _eq(a, b)
    if op == "!=":
        return not _eq(a, b)
    if op == "in":
        return isinstance(b, list | str) and (
            a in b if isinstance(b, list) else isinstance(a, str) and a in b
        )
    return _compare(op, a, b)
