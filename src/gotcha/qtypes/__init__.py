"""Tipos de questão. Importar este pacote registra todos os tipos."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, TypeAdapter

from .base import (
    REGISTRY,
    Question,
    QuestionBase,
    grade_question,
    group_of,
    parse_response,
    public_view,
    summarize_question,
    validate_question,
)
from .choice import MultipleChoice, MultipleSelect
from .dragdrop import DragDrop
from .hotarea import HotArea
from .interactive import ActiveScreen, Lab, SelfAssessed
from .ordering import BuildList

AnyQuestion = Annotated[
    MultipleChoice | MultipleSelect | BuildList | DragDrop | HotArea | ActiveScreen | Lab | SelfAssessed,
    Field(discriminator="type"),
]
_ADAPTER: TypeAdapter[Any] = TypeAdapter(AnyQuestion)


def parse_question(data: dict[str, Any]) -> QuestionBase:
    result: QuestionBase = _ADAPTER.validate_python(data)
    return result


__all__ = [
    "REGISTRY",
    "ActiveScreen",
    "BuildList",
    "DragDrop",
    "HotArea",
    "Lab",
    "MultipleChoice",
    "MultipleSelect",
    "Question",
    "QuestionBase",
    "SelfAssessed",
    "grade_question",
    "group_of",
    "parse_question",
    "parse_response",
    "public_view",
    "summarize_question",
    "validate_question",
]  # fmt: skip
