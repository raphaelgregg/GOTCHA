"""Motor declarativo do Active Screen.

Uma tela é **dado**, não código: lista fechada de componentes, estado tipado, ações e condições em
JSON (sintaxe JSON Logic). O servidor reexecuta o registro de eventos do usuário a partir do estado
inicial, então o resultado não pode ser forjado e o gabarito nunca vai para o navegador.
O navegador roda uma porta equivalente deste motor, verificada pelos mesmos vetores de teste.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from .logic import LogicError, evaluate, validate

MAX_EVENTS = 1000
MAX_ACTIONS_PER_EVENT = 50
MAX_COMPONENTS = 300
MAX_TEXT = 500

ComponentType = Literal[
    "text", "image", "button", "input", "select", "checkbox", "radio_group",
    "tabs", "menu", "table", "toggle",
]  # fmt: skip
_DEFAULTS: dict[str, Any] = {"string": "", "number": 0, "bool": False, "list": []}


class StateVar(BaseModel):
    type: Literal["string", "number", "bool", "list"]
    initial: Any = None

    def start_value(self) -> Any:
        return copy.deepcopy(self.initial if self.initial is not None else _DEFAULTS[self.type])


class Action(BaseModel):
    do: Literal["set", "toggle", "goto", "message", "append"]
    var: str | None = None
    value: Any = None
    screen: str | None = None
    text: str | None = None


class Option(BaseModel):
    id: str
    label: str = ""


class MenuItem(BaseModel):
    id: str
    label: str = ""
    on_click: list[Action] = Field(default_factory=list, max_length=20)


class Row(BaseModel):
    id: str
    cells: list[str] = Field(default_factory=list)


class Component(BaseModel):
    id: str
    type: ComponentType
    label: str = ""
    text: str = ""
    asset: str | None = None
    bind: str | None = None
    options: list[Option] = Field(default_factory=list, max_length=100)
    items: list[MenuItem] = Field(default_factory=list, max_length=100)
    columns: list[str] = Field(default_factory=list, max_length=20)
    rows: list[Row] = Field(default_factory=list, max_length=200)
    visible_if: Any = None
    enabled_if: Any = None
    on_click: list[Action] = Field(default_factory=list, max_length=20)
    on_change: list[Action] = Field(default_factory=list, max_length=20)


class Screen(BaseModel):
    id: str
    title: str = ""
    components: list[Component] = Field(default_factory=list, max_length=200)


class ScreenSpec(BaseModel):
    screens: list[Screen] = Field(min_length=1, max_length=50)
    state: dict[str, StateVar] = Field(default_factory=dict)
    start: str


class Check(BaseModel):
    id: str
    label: str = ""
    when: Any
    points: int = Field(default=1, ge=1, le=100)


@dataclass
class Run:
    state: dict[str, Any]
    screen: str
    messages: list[str] = field(default_factory=list)
    applied: int = 0
    ignored: int = 0


def _logic_errors(label: str, expr: Any) -> list[str]:
    if expr is None:
        return []
    try:
        validate(expr)
    except LogicError as exc:
        return [f"{label}: {exc}"]
    return []


def _action_errors(where: str, actions: list[Action], spec: ScreenSpec) -> list[str]:
    errors: list[str] = []
    screens = {s.id for s in spec.screens}
    for a in actions:
        if a.do in {"set", "toggle", "append"}:
            if a.var not in spec.state:
                errors.append(f"{where}: a variável {a.var!r} não existe.")
            elif a.do == "toggle" and spec.state[a.var].type != "bool":
                errors.append(f"{where}: `toggle` exige variável booleana ({a.var!r}).")
            elif a.do == "append" and spec.state[a.var].type != "list":
                errors.append(f"{where}: `append` exige variável do tipo lista ({a.var!r}).")
        elif a.do == "goto" and a.screen not in screens:
            errors.append(f"{where}: a tela {a.screen!r} não existe.")
        elif a.do == "message" and not a.text:
            errors.append(f"{where}: `message` exige texto.")
    return errors


def validate_screen(spec: ScreenSpec) -> list[str]:
    errors: list[str] = []
    ids = [s.id for s in spec.screens]
    if len(set(ids)) != len(ids):
        errors.append("Há telas com identificador repetido.")
    if spec.start not in ids:
        errors.append(f"A tela inicial {spec.start!r} não existe.")
    components = [c for s in spec.screens for c in s.components]
    if len(components) > MAX_COMPONENTS:
        errors.append(f"Mais de {MAX_COMPONENTS} componentes.")
    cids = [c.id for c in components]
    if len(set(cids)) != len(cids):
        errors.append("Há componentes com identificador repetido.")
    for c in components:
        where = f"componente {c.id!r}"
        if c.bind is not None and c.bind not in spec.state:
            errors.append(f"{where}: a variável {c.bind!r} não existe.")
        if len({o.id for o in c.options}) != len(c.options):
            errors.append(f"{where}: opções com identificador repetido.")
        errors += _logic_errors(f"{where} (visible_if)", c.visible_if)
        errors += _logic_errors(f"{where} (enabled_if)", c.enabled_if)
        errors += _action_errors(where, c.on_click + c.on_change, spec)
        for item in c.items:
            errors += _action_errors(f"{where}/{item.id}", item.on_click, spec)
    return errors


def _truthy(expr: Any, state: dict[str, Any]) -> bool:
    return True if expr is None else bool(evaluate(expr, state))


def _accepts(var_type: str, value: Any) -> bool:
    if var_type == "string":
        return isinstance(value, str) and len(value) <= MAX_TEXT
    if var_type == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    if var_type == "bool":
        return isinstance(value, bool)
    return isinstance(value, list)


def _change_value(comp: Component, value: Any, spec: ScreenSpec) -> tuple[bool, Any]:
    """Valida o valor de um evento `change` conforme o tipo do componente."""
    kind = comp.type
    if kind in {"select", "radio_group", "tabs"}:
        return (isinstance(value, str) and value in {o.id for o in comp.options}), value
    if kind == "table":
        return (isinstance(value, str) and value in {r.id for r in comp.rows}), value
    if kind in {"checkbox", "toggle"}:
        return isinstance(value, bool), value
    if kind == "input" and comp.bind in spec.state:
        return _accepts(spec.state[comp.bind].type, value), value
    return False, None


def _apply(actions: list[Action], spec: ScreenSpec, run: Run) -> None:
    for a in actions[:MAX_ACTIONS_PER_EVENT]:
        if a.do == "goto" and a.screen in {s.id for s in spec.screens}:
            run.screen = a.screen
        elif a.do == "message" and a.text:
            run.messages.append(a.text[:MAX_TEXT])
        elif a.var in spec.state:
            declared = spec.state[a.var].type
            if a.do == "set" and _accepts(declared, a.value):
                run.state[a.var] = copy.deepcopy(a.value)
            elif a.do == "toggle" and declared == "bool":
                run.state[a.var] = not run.state[a.var]
            elif a.do == "append" and declared == "list" and len(run.state[a.var]) < 1000:
                run.state[a.var].append(copy.deepcopy(a.value))


def replay(spec: ScreenSpec, events: list[dict[str, Any]]) -> Run:
    run = Run(state={k: v.start_value() for k, v in spec.state.items()}, screen=spec.start)
    screens = {s.id: s for s in spec.screens}
    for index, event in enumerate(events):
        if index >= MAX_EVENTS:
            run.ignored += len(events) - MAX_EVENTS
            break
        if not _handle(event, spec, screens, run):
            run.ignored += 1
        else:
            run.applied += 1
    return run


def _handle(event: dict[str, Any], spec: ScreenSpec, screens: dict[str, Screen], run: Run) -> bool:
    comp = next((c for c in screens[run.screen].components if c.id == event.get("component")), None)
    if comp is None:
        return False
    try:
        if not (_truthy(comp.visible_if, run.state) and _truthy(comp.enabled_if, run.state)):
            return False
    except LogicError:
        return False
    kind, value = event.get("type"), event.get("value")
    if kind == "change":
        ok, clean = _change_value(comp, value, spec)
        if not ok or comp.bind not in spec.state:
            return False
        run.state[comp.bind] = clean
        _apply(comp.on_change, spec, run)
        return True
    if kind == "click":
        if comp.type == "button":
            _apply(comp.on_click, spec, run)
            return True
        if comp.type == "menu":
            item = next((i for i in comp.items if i.id == value), None)
            if item is None:
                return False
            _apply(item.on_click, spec, run)
            return True
    return False
