"""Migração do modelo v1 (importadores e bancos existentes) para o modelo canônico v2."""

from __future__ import annotations

import json
from typing import Any, Literal

from gotcha.domain.models import Question as V1Question
from gotcha.domain.models import QuestionKind

from .base import Conversion, QuestionBase
from .blocks import Block, HtmlBlock, ImageBlock, ParagraphBlock
from .choice import MultipleChoice, MultipleSelect, Option
from .interactive import SelfAssessed

NO_ANSWER_TEXT = "Resposta não disponível no arquivo importado. Confira na fonte original."


def _image(name: str, sha: str | None) -> ImageBlock:
    return ImageBlock(asset=sha, name=name, alt=name)


def v1_to_v2(q: V1Question) -> QuestionBase:
    warnings = list(q.warnings)
    prompt: list[Block] = [HtmlBlock(html=q.stem)] if q.stem else []
    answer_blocks: list[Block] = []
    for img in q.images:
        block = _image(img.name, img.sha)
        if img.missing:
            warnings.append(f"Anexo ausente: {img.name}.")
        (answer_blocks if img.role == "answer" else prompt).append(block)
    explanation: list[Block] = [ParagraphBlock(text=q.explanation)] if q.explanation else []
    common: dict[str, Any] = {
        "topic": q.topic, "number": q.number, "prompt": prompt, "explanation": explanation,
        "case_id": q.case_id, "exam_id": q.exam_id, "batch_id": q.batch_id,
    }  # fmt: skip
    if q.id:
        common["uid"] = f"q_{q.id}"
    letters = {c.letter for c in q.choices}
    options = [Option(id=c.letter, blocks=[ParagraphBlock(text=c.text)]) for c in q.choices]
    missing = any(img.missing for img in q.images)
    status: Literal["ok", "partial", "manual_required"] = "partial" if missing else "ok"

    if q.kind is not QuestionKind.INTERACTIVE and q.answer and set(q.answer) <= letters:
        conv = Conversion(
            status=status, preserved=["enunciado", "alternativas", "gabarito"], warnings=warnings
        )
        if q.kind is QuestionKind.MULTIPLE or len(q.answer) > 1:
            return MultipleSelect(options=options, correct=list(q.answer), conversion=conv, **common)
        variant: Literal["standard", "true_false"] = (
            "true_false" if q.kind is QuestionKind.TRUE_FALSE else "standard"
        )
        return MultipleChoice(
            options=options, correct=q.answer[0], variant=variant, conversion=conv, **common
        )

    # Sem gabarito utilizável (ou tipo interativo): nada se perde, vira questão autoavaliada.
    lost: list[str] = []
    if q.kind is not QuestionKind.INTERACTIVE:
        common["prompt"] = prompt + [ParagraphBlock(text=f"{c.letter}) {c.text}") for c in q.choices]
        warnings.append("Sem gabarito: converta para múltipla escolha no editor.")
        status = "manual_required"
        lost.append("gabarito")
    if not answer_blocks:
        answer_blocks = [ParagraphBlock(text=NO_ANSWER_TEXT)]
        if q.kind is QuestionKind.INTERACTIVE:
            warnings.append("Resposta de referência ausente; defina-a no editor.")
    return SelfAssessed(
        answer_blocks=answer_blocks,
        conversion=Conversion(
            status=status, preserved=["enunciado", "imagens"], lost=lost, warnings=warnings
        ),
        **common,
    )


def load_question(raw: str | dict[str, Any]) -> QuestionBase:
    """Lê uma questão armazenada em qualquer versão do esquema."""
    from . import parse_question

    data = json.loads(raw) if isinstance(raw, str) else raw
    if data.get("schema_version") == 2 and "type" in data:
        return parse_question(data)
    return v1_to_v2(V1Question.model_validate(data))
