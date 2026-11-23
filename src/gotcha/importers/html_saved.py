"""Importador de páginas HTML salvas de simulados (cartões de questão com alternativas)."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from gotcha.domain.models import Choice, ImageRef, ParsedBatch, Question, QuestionKind
from gotcha.domain.sanitize import clean_html

from .base import Source, register
from .common import decode_text, infer_kind, parse_letters, sha256, validate_answer

_NUMBER = re.compile(r"Question\s*#?\s*(\d+)", re.I)
_TOPIC = re.compile(r"Topic\s*(\d+)", re.I)


def _lookup_asset(src_attr: str, assets: dict[str, bytes]) -> tuple[str, bytes | None]:
    name = src_attr.replace("\\", "/").rstrip("/").split("/")[-1]
    data = assets.get(src_attr) or assets.get(src_attr.lstrip("./")) or assets.get(name)
    return name, data


class HtmlImporter:
    name = "html"

    def sniff(self, src: Source) -> float:
        return 0.95 if b"exam-question-card" in src.data else 0.0

    def parse(self, src: Source) -> ParsedBatch:
        soup = BeautifulSoup(decode_text(src.data), "lxml")
        cards = soup.select("div.exam-question-card")
        if not cards:
            raise ValueError("Não há questões na página: nenhum cartão de questão encontrado.")
        batch = ParsedBatch(format=self.name, title=src.filename)
        for card in cards:
            batch.questions.append(self._question(card, src, batch))
        return batch

    def _question(self, card: Tag, src: Source, batch: ParsedBatch) -> Question:
        header = card.select_one(".card-header")
        head_text = header.get_text(" ", strip=True) if header else ""
        number = int(m.group(1)) if (m := _NUMBER.search(head_text)) else len(batch.questions) + 1
        topic = int(m.group(1)) if (m := _TOPIC.search(head_text)) else 1
        warnings: list[str] = []
        images: list[ImageRef] = []

        def collect(img: Tag, role: str) -> None:
            name, data = _lookup_asset(str(img.get("src", "")), src.assets)
            sha = sha256(data) if data is not None else None
            if data is not None and sha is not None:
                batch.assets[sha] = data
            else:
                warnings.append(f"Anexo ausente: {name}.")
            images.append(
                ImageRef(name=name, sha=sha, role="answer" if role == "answer" else "stem")
            )

        stem_el = next(
            (
                p
                for p in card.select(".question-body p.card-text")
                if "question-answer" not in (p.get("class") or [])
            ),
            None,
        )
        stem_html = ""
        if stem_el is not None:
            for img in stem_el.find_all("img"):
                collect(img, "stem")
                img.decompose()
            stem_html = clean_html(stem_el.decode_contents())

        choices = []
        voted: list[str] = []
        for item in card.select(".multi-choice-item"):
            letter = str(item.get("data-choice-letter") or "").strip().upper()
            letter_el = item.select_one(".multi-choice-letter")
            if not letter and letter_el:
                letter = letter_el.get_text(strip=True).rstrip(".)").upper()
            if item.select_one(".most-voted-answer-badge"):
                voted.append(letter)
            for junk in item.select(".multi-choice-letter, .badge"):
                junk.decompose()
            choices.append(Choice(letter=letter, text=item.get_text(" ", strip=True)))

        answer_el = card.select_one(".correct-answer")
        answer: list[str] = []
        if answer_el is not None:
            for img in answer_el.find_all("img"):
                collect(img, "answer")
            answer = parse_letters(answer_el.get_text("", strip=True))
        for img in card.select(".answer-description img"):
            collect(img, "answer")

        kind = infer_kind(choices, answer)
        if kind is not QuestionKind.INTERACTIVE:
            warnings += validate_answer(choices, answer)
            if voted and sorted(set(voted)) != sorted(answer):
                warnings.append(
                    f"A resposta mais votada ({', '.join(sorted(set(voted)))}) "
                    f"diverge do gabarito publicado ({', '.join(answer) or 'vazio'})."
                )
        return Question(
            topic=topic, number=number, kind=kind, stem=stem_html, choices=choices,
            answer=answer if kind is not QuestionKind.INTERACTIVE else [],
            images=images, warnings=warnings,
        )  # fmt: skip


register(HtmlImporter())
