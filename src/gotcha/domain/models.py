"""Modelos de domínio compartilhados por importadores, armazenamento e API."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class QuestionKind(StrEnum):
    SINGLE = "single"
    MULTIPLE = "multiple"
    TRUE_FALSE = "true_false"
    INTERACTIVE = "interactive"  # hot area, arrastar-e-soltar, simulação: autoavaliada


class Choice(BaseModel):
    letter: str
    text: str


class ImageRef(BaseModel):
    """Imagem associada à questão. Sem `sha` significa anexo ausente."""

    name: str
    sha: str | None = None
    role: Literal["stem", "answer"] = "stem"

    @property
    def missing(self) -> bool:
        return self.sha is None


class CaseStudy(BaseModel):
    id: str
    title: str = "Estudo de caso"
    text: str


class Question(BaseModel):
    id: str | None = None
    exam_id: str | None = None
    batch_id: str | None = None
    topic: int = 1
    number: int
    kind: QuestionKind
    stem: str
    choices: list[Choice] = Field(default_factory=list)
    answer: list[str] = Field(default_factory=list)
    explanation: str = ""
    images: list[ImageRef] = Field(default_factory=list)
    case_id: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @property
    def scored_automatically(self) -> bool:
        return self.kind is not QuestionKind.INTERACTIVE

    @property
    def key(self) -> tuple[int, int]:
        """Chave estável dentro de um exame: (tópico, número)."""
        return (self.topic, self.number)


class ParsedBatch(BaseModel):
    """Resultado de um importador: rascunhos que aguardam revisão."""

    format: str
    title: str = ""
    questions: list[Question] = Field(default_factory=list)
    cases: list[CaseStudy] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    # nome do arquivo de imagem -> bytes (não serializado)
    assets: dict[str, bytes] = Field(default_factory=dict, exclude=True)
