"""Analisador de blocos de texto, compartilhado por TXT simples e PDF.

Cada questão começa em uma linha de título (ex.: `Q3` ou `Question #3`), tem enunciado,
alternativas `A.`/`A)`, e termina em uma linha de gabarito. Seções de explicação, referência e
comentários da comunidade são tratadas à parte (comentários são descartados).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from gotcha.domain.models import CaseStudy, Choice, ImageRef, Question, QuestionKind

from .common import fold, infer_kind, parse_letters, plain_to_html, validate_answer

_OPTION = re.compile(r"^([A-F])[\.\)]\s+(.+)$")
_IMAGE_PLACEHOLDER = re.compile(r"\[INSERIR IMAGEM MANUALMENTE:\s*([^\]]+)\]", re.I)
_MANUAL_PLACEHOLDER = re.compile(r"\[CONFIGURACAO MANUAL:\s*([^\]]*)\]", re.I)
_INTERACTIVE_LABEL = re.compile(
    r"^(hotspot|drag\s*drop|area quente|arrastar|simulacao|simulation|lab\b)"
)
_CASE_LABEL = re.compile(r"^(estudo de caso|case study)")
_EXPLANATION = re.compile(r"^explanation|^explicacao", re.I)
_SKIP_SECTION = re.compile(r"^(reference|community discussion)", re.I)
_FOOTER = re.compile(r"^page \d+( of \d+)?$", re.I)


@dataclass(frozen=True)
class BlockRules:
    heading: re.Pattern[str]  # grupo nomeado `n`
    answer: re.Pattern[str]  # grupo nomeado `a`


@dataclass
class _Draft:
    number: int
    stem_lines: list[str] = field(default_factory=list)
    choices: list[Choice] = field(default_factory=list)
    answer: list[str] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    interactive: bool = False
    is_case: bool = False


def parse_blocks(
    lines: list[str], rules: BlockRules
) -> tuple[list[Question], list[CaseStudy], list[str]]:
    drafts: list[_Draft] = []
    current: list[str] | None = None
    chunks: list[tuple[int, list[str]]] = []
    for raw in lines:
        line = raw.strip()
        m = rules.heading.match(line)
        if m:
            current = []
            chunks.append((int(m.group("n")), current))
        elif current is not None and line:
            current.append(line)
    for number, chunk in chunks:
        drafts.append(_read_block(number, chunk, rules))
    cases = _share_case_context(drafts)
    questions = [_finalize(d) for d in drafts]
    seen: set[int] = set()
    warnings: list[str] = []
    for q in questions:
        if q.number in seen:
            warnings.append(f"Número de questão repetido: {q.number}.")
        seen.add(q.number)
    return questions, cases, warnings


def _read_block(number: int, lines: list[str], rules: BlockRules) -> _Draft:
    d = _Draft(number=number)
    body: list[str] = []
    section = "body"
    for line in lines:
        am = rules.answer.match(line)
        if am:
            d.answer = parse_letters(am.group("a") or "")
            section = "answer"
        elif _EXPLANATION.match(line):
            section = "explanation"
        elif _SKIP_SECTION.match(line):
            section = "skip"
        elif _FOOTER.match(line):
            continue
        elif section == "body":
            body.append(line)
        elif section == "explanation":
            d.explanation.append(line)
    body = _consume_markers(d, body)
    _split_stem_and_choices(d, body)
    return d


def _consume_markers(d: _Draft, body: list[str]) -> list[str]:
    kept: list[str] = []
    for i, line in enumerate(body):
        folded = fold(line)
        if i == 0 and len(line) <= 70 and _CASE_LABEL.match(folded):
            d.is_case = True
            kept.append(line)
            continue
        if i == 0 and len(line) <= 70 and _INTERACTIVE_LABEL.match(folded):
            d.interactive = True
            continue
        img = _IMAGE_PLACEHOLDER.search(line)
        if img:
            d.images.append(ImageRef(name=img.group(1).strip()))
            d.warnings.append(f"Anexo ausente: {img.group(1).strip()}.")
            continue
        manual = _MANUAL_PLACEHOLDER.search(line)
        if manual:
            d.interactive = True
            d.warnings.append(f"Configuração manual requerida ({manual.group(1).strip()}).")
            continue
        kept.append(line)
    return kept


def _split_stem_and_choices(d: _Draft, body: list[str]) -> None:
    expected = "A"
    for line in body:
        m = _OPTION.match(line)
        if m and m.group(1) == expected:
            d.choices.append(Choice(letter=expected, text=m.group(2).strip()))
            expected = chr(ord(expected) + 1)
        elif m and m.group(1) == "A" and d.choices:
            # um novo "A" reinicia: o que parecia alternativa era parte do enunciado
            d.stem_lines.extend(f"{c.letter}. {c.text}" for c in d.choices)
            d.choices = [Choice(letter="A", text=m.group(2).strip())]
            expected = "B"
        elif d.choices:
            d.choices[-1] = Choice(letter=d.choices[-1].letter, text=f"{d.choices[-1].text} {line}")
        else:
            d.stem_lines.append(line)


def _share_case_context(drafts: list[_Draft]) -> list[CaseStudy]:
    """Estudos de caso consecutivos repetem o contexto: guarda-o uma vez e o referencia."""
    cases: list[CaseStudy] = []
    i = 0
    while i < len(drafts):
        if not drafts[i].is_case:
            i += 1
            continue
        j = i
        while j + 1 < len(drafts) and drafts[j + 1].is_case:
            j += 1
        group = drafts[i : j + 1]
        prefix = _common_prefix([d.stem_lines for d in group])
        if len(group) > 1 and len(prefix) >= 3:
            case = CaseStudy(id=f"case-{len(cases) + 1}", text=plain_to_html("\n".join(prefix[1:])))
            cases.append(case)
            for d in group:
                d.stem_lines = d.stem_lines[len(prefix) :] or d.stem_lines
                d.warnings.append(f"case:{case.id}")
        else:
            for d in group:
                d.stem_lines = d.stem_lines[1:] or d.stem_lines
        i = j + 1
    return cases


def _common_prefix(lists: list[list[str]]) -> list[str]:
    prefix: list[str] = []
    for column in zip(*lists, strict=False):
        if len(set(column)) != 1:
            break
        prefix.append(column[0])
    return prefix


def _finalize(d: _Draft) -> Question:
    case_id = next((w[5:] for w in d.warnings if w.startswith("case:")), None)
    warnings = [w for w in d.warnings if not w.startswith("case:")]
    hint = QuestionKind.INTERACTIVE if d.interactive else None
    kind = infer_kind(d.choices, d.answer, hint)
    if kind is not QuestionKind.INTERACTIVE:
        warnings += validate_answer(d.choices, d.answer)
    return Question(
        number=d.number,
        kind=kind,
        stem=plain_to_html("\n".join(d.stem_lines)),
        choices=d.choices,
        answer=d.answer if kind is not QuestionKind.INTERACTIVE else [],
        explanation="\n".join(d.explanation),
        images=d.images,
        case_id=case_id,
        warnings=warnings,
    )
