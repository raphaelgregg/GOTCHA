"""Blocos de conteúdo: a ordem dos blocos é a ordem de exibição (reposicionar = reordenar)."""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from gotcha.domain.sanitize import clean_html, to_plain_text

SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _asset(value: str | None) -> str | None:
    if value is not None and not SHA256.match(value):
        raise ValueError("O recurso deve ser referenciado pelo SHA-256 (64 caracteres hexadecimais).")
    return value


class ParagraphBlock(BaseModel):
    type: Literal["paragraph"] = "paragraph"
    text: str


class HtmlBlock(BaseModel):
    type: Literal["html"] = "html"
    html: str

    @field_validator("html")
    @classmethod
    def _sanitize(cls, value: str) -> str:
        return clean_html(value)


class TableBlock(BaseModel):
    type: Literal["table"] = "table"
    rows: list[list[str]]
    header: bool = True


class CodeBlock(BaseModel):
    type: Literal["code"] = "code"
    code: str
    language: str = ""


class ImageBlock(BaseModel):
    """Imagem por referência ao recurso. Sem `asset`, é um anexo ausente (identificado por `name`)."""

    type: Literal["image"] = "image"
    asset: str | None = None
    name: str = ""
    alt: str = ""
    width_pct: int = Field(default=100, ge=10, le=100)
    align: Literal["left", "center", "right"] = "center"
    caption: str = ""

    _check = field_validator("asset")(_asset)

    @property
    def missing(self) -> bool:
        return self.asset is None


class AttachmentBlock(BaseModel):
    type: Literal["attachment"] = "attachment"
    asset: str | None = None
    label: str = ""

    _check = field_validator("asset")(_asset)


Block = Annotated[
    ParagraphBlock | HtmlBlock | TableBlock | CodeBlock | ImageBlock | AttachmentBlock,
    Field(discriminator="type"),
]


def asset_ids(blocks: list[Block]) -> set[str]:
    return {b.asset for b in blocks if isinstance(b, ImageBlock | AttachmentBlock) and b.asset}


def blocks_text(blocks: list[Block]) -> str:
    parts: list[str] = []
    for b in blocks:
        if isinstance(b, ParagraphBlock):
            parts.append(b.text)
        elif isinstance(b, HtmlBlock):
            parts.append(to_plain_text(b.html))
        elif isinstance(b, TableBlock):
            parts.extend(" | ".join(r) for r in b.rows)
        elif isinstance(b, CodeBlock):
            parts.append(b.code)
    return "\n".join(parts)
