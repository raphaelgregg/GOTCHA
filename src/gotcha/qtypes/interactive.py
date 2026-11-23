"""Active Screen, Lab e o tipo de transição `self_assessed`."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from gotcha.domain.grading import Grade, Outcome

from .base import QuestionBase, TypeSpec, grade_from_score, register
from .blocks import Block
from .logic import LogicError, evaluate, validate
from .screen import Check, ScreenSpec, replay, validate_screen


class ScreenResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[dict[str, Any]] = Field(default_factory=list, max_length=1100)


class LabResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[dict[str, Any]] = Field(default_factory=list, max_length=1100)
    attested: list[str] = Field(default_factory=list, max_length=200)


class SelfResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    self_mark: bool | None = None


def _expr_errors(label: str, expr: Any) -> list[str]:
    try:
        validate(expr)
    except LogicError as exc:
        return [f"{label}: {exc}"]
    return []


def _screen_errors(screen: ScreenSpec, completion: Any, checks: list[Check]) -> list[str]:
    errors = validate_screen(screen)
    if completion is None and not checks:
        errors.append("Defina a condição de conclusão ou ao menos uma verificação.")
    if completion is not None:
        errors += _expr_errors("completion", completion)
    ids = [c.id for c in checks]
    if len(set(ids)) != len(ids):
        errors.append("Há verificações com identificador repetido.")
    for c in checks:
        errors += _expr_errors(f"verificação {c.id!r}", c.when)
    return errors


def _score_screen(
    screen: ScreenSpec,
    completion: Any,
    checks: list[Check],
    events: list[dict[str, Any]],
    partial: bool,
) -> float:
    run = replay(screen, events)
    done = bool(evaluate(completion, run.state)) if completion is not None else None
    if checks:
        total = sum(c.points for c in checks)
        earned = sum(c.points for c in checks if bool(evaluate(c.when, run.state)))
        ratio = earned / total
        if done is None:
            done = earned == total
        return ratio if partial and not done else (1.0 if done else 0.0)
    return 1.0 if done else 0.0


def _screen_public(screen: ScreenSpec) -> dict[str, Any]:
    return {"screen": screen.model_dump(mode="json")}


def _checks_key(completion: Any, checks: list[Check]) -> dict[str, Any]:
    return {"completion": completion, "checks": [c.model_dump(mode="json") for c in checks]}


class ActiveScreen(QuestionBase):
    type: Literal["active_screen"] = "active_screen"
    screen: ScreenSpec
    completion: Any = None
    checks: list[Check] = Field(default_factory=list, max_length=50)
    fidelity: Literal["reconstructed", "approximate", "screenshot_only"] = "reconstructed"
    limitations: list[str] = Field(default_factory=list)


register(
    TypeSpec(
        name="active_screen",
        model=ActiveScreen,
        response=ScreenResponse,
        grade=lambda q, r: grade_from_score(
            _score_screen(q.screen, q.completion, q.checks, r.events, q.scoring.partial),
            q.scoring.partial,
        ),
        public=lambda q, _s: {
            **_screen_public(q.screen),
            "fidelity": q.fidelity,
            "limitations": list(q.limitations),
        },
        key=lambda q: _checks_key(q.completion, q.checks),
        validate=lambda q: _screen_errors(q.screen, q.completion, q.checks),
        answered=lambda r: bool(r.events),
        interactive=True,
    )
)


class LabStep(BaseModel):
    id: str
    title: str = ""
    instructions: list[Block] = Field(default_factory=list)


class Environment(BaseModel):
    kind: str = ""
    description: str = ""


LabMode = Literal["simulated", "external_instructions", "real"]


class Lab(QuestionBase):
    type: Literal["lab"] = "lab"
    mode: LabMode
    objectives: list[str] = Field(default_factory=list)
    environment: Environment = Field(default_factory=Environment)
    resources: list[str] = Field(default_factory=list)
    steps: list[LabStep] = Field(default_factory=list, max_length=100)
    screen: ScreenSpec | None = None  # só no laboratório simulado
    completion: Any = None
    checks: list[Check] = Field(default_factory=list, max_length=50)


def _validate_lab(q: Lab) -> list[str]:
    errors: list[str] = []
    if q.mode == "simulated":
        if q.screen is None:
            errors.append("Laboratório simulado exige uma tela simulada.")
        else:
            errors += _screen_errors(q.screen, q.completion, q.checks)
    else:
        if not q.steps:
            errors.append("Defina ao menos uma etapa.")
        if q.screen is not None:
            errors.append("Somente o laboratório simulado possui tela simulada.")
    ids = [s.id for s in q.steps]
    if len(set(ids)) != len(ids):
        errors.append("Há etapas com identificador repetido.")
    return errors


def _grade_lab(q: Lab, r: LabResponse) -> Grade:
    if q.mode == "simulated" and q.screen is not None:
        score = _score_screen(q.screen, q.completion, q.checks, r.events, q.scoring.partial)
        g = grade_from_score(score, q.scoring.partial, "lab")
        return g
    steps = {s.id for s in q.steps}
    score = len(set(r.attested) & steps) / len(steps) if steps else 0.0
    return Grade(score, Outcome.SELF_CORRECT if score >= 1.0 else Outcome.SELF_INCORRECT, "self")


def _public_lab(q: Lab, _seed: int) -> dict[str, Any]:
    view: dict[str, Any] = {
        "mode": q.mode,
        "objectives": list(q.objectives),
        "environment": q.environment.model_dump(),
        "resources": list(q.resources),
        "steps": [s.model_dump(mode="json") for s in q.steps],
    }
    if q.screen is not None:
        view.update(_screen_public(q.screen))
    return view


register(
    TypeSpec(
        name="lab",
        model=Lab,
        response=LabResponse,
        grade=_grade_lab,
        public=_public_lab,
        key=lambda q: _checks_key(q.completion, q.checks) if q.mode == "simulated" else {},
        validate=_validate_lab,
        answered=lambda r: bool(r.events or r.attested),
        interactive=True,
    )
)


class SelfAssessed(QuestionBase):
    """Tipo de transição: enunciado e imagens com resposta de referência, autoavaliada."""

    type: Literal["self_assessed"] = "self_assessed"
    answer_blocks: list[Block] = Field(default_factory=list)


def _grade_self(_: SelfAssessed, r: SelfResponse) -> Grade:
    ok = bool(r.self_mark)
    return Grade(1.0 if ok else 0.0, Outcome.SELF_CORRECT if ok else Outcome.SELF_INCORRECT, "self")


register(
    TypeSpec(
        name="self_assessed",
        model=SelfAssessed,
        response=SelfResponse,
        grade=_grade_self,
        public=lambda q, _s: {},
        key=lambda q: {"answer_blocks": [b.model_dump(mode="json") for b in q.answer_blocks]},
        validate=lambda q: [] if q.answer_blocks else ["Informe a resposta de referência."],
        answered=lambda r: r.self_mark is not None,
        interactive=True,
    )
)
