"""Sanitização de HTML importado: permite só marcação de texto, tabelas e código."""

from __future__ import annotations

import re

import nh3

ALLOWED_TAGS = {
    "p", "br", "b", "strong", "i", "em", "u", "code", "pre", "ul", "ol", "li", "blockquote",
    "table", "thead", "tbody", "tr", "th", "td", "span", "div", "sub", "sup", "h4", "h5",
}  # fmt: skip


def clean_html(html: str) -> str:
    return nh3.clean(html, tags=ALLOWED_TAGS, attributes={}, link_rel=None, strip_comments=True)


def to_plain_text(html: str) -> str:
    """Texto simples a partir de HTML, com uma linha por bloco."""
    html = re.sub(r"</(p|div|li|tr|h\d)>|<br\s*/?>", "\n", html, flags=re.I)
    text = nh3.clean(html, tags=set())
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)
