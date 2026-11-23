"""Estudo de caso: contexto compartilhado, guardado uma vez e referenciado pelas questões."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field

from .blocks import Block


class CaseSection(BaseModel):
    id: str
    title: str = ""
    blocks: list[Block] = Field(default_factory=list)


class CaseStudyDoc(BaseModel):
    id: str
    title: str = "Estudo de caso"
    sections: list[CaseSection] = Field(default_factory=list, max_length=50)

    def fingerprint(self) -> str:
        content = self.model_dump(mode="json", exclude={"id"})
        canon = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()
