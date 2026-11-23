"""Imagens de PDF: extraídas sem perda, com posição, e ligadas à questão pela ordem de leitura.

Regra de associação: em ordem de leitura (página, de cima para baixo), cada imagem pertence à última
questão que apareceu. Antes dos marcadores `Explanation` e `Correct Answer:` ela é do enunciado; depois, é
a imagem da resposta. Imagens que se repetem na maioria das páginas (logotipos, faixas) são decorativas.
Nada é descartado em silêncio: o que não tem dono ou não pôde ser extraído vira aviso.
"""

from __future__ import annotations

import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal

from gotcha.qtypes.assets import MAX_PIXELS, sha256_hex

_EXPLANATION = re.compile(r"(?i)^(explanation|explicacao)")
DECORATIVE_MIN_PAGES = 3
DECORATIVE_RATIO = 0.5


@dataclass
class PageImage:
    page: int
    y: float  # topo da imagem (coordenada do PDF: maior = mais acima)
    png: bytes
    name: str

    @property
    def sha(self) -> str:
        return sha256_hex(self.png)


@dataclass
class Marker:
    page: int
    y: float
    kind: Literal["heading", "explanation", "answer"]
    number: int | None = None


@dataclass
class Association:
    placed: list[tuple[int, str, PageImage]] = field(default_factory=list)  # (questão, papel, imagem)
    orphans: list[PageImage] = field(default_factory=list)


def associate(markers: list[Marker], images: list[PageImage]) -> Association:
    stream: list[tuple[int, float, int, Marker | PageImage]] = [(m.page, -m.y, 0, m) for m in markers] + [
        (i.page, -i.y, 1, i) for i in images
    ]
    stream.sort(key=lambda t: (t[0], t[1], t[2]))
    result = Association()
    current: int | None = None
    after_answer_label = False
    for *_, item in stream:
        if isinstance(item, Marker):
            if item.kind == "heading":
                current, after_answer_label = item.number, False
            else:
                after_answer_label = True
        elif current is None:
            result.orphans.append(item)
        else:
            result.placed.append((current, "answer" if after_answer_label else "stem", item))
    return result


def read_markers(doc: Any, heading: re.Pattern[str], answer: re.Pattern[str]) -> list[Marker]:
    markers: list[Marker] = []
    for pi in range(len(doc)):
        tp = doc[pi].get_textpage()
        text = tp.get_text_range() or ""
        for m in re.finditer(r"[^\r\n]+", text):
            line = m.group().strip()
            h = heading.match(line)
            if h:
                kind: Literal["heading", "explanation", "answer"] = "heading"
                number: int | None = int(h.group("n"))
            elif _EXPLANATION.match(line):
                kind, number = "explanation", None
            elif answer.match(line):
                kind, number = "answer", None
            else:
                continue
            _, _, _, top = tp.get_charbox(m.start())
            markers.append(Marker(pi, top, kind, number))
    return markers


def read_images(doc: Any) -> tuple[list[PageImage], int]:
    """Extrai todas as imagens embutidas como PNG (sem perda). Devolve também quantas falharam."""
    images: list[PageImage] = []
    failed = 0
    for pi in range(len(doc)):
        for k, obj in enumerate(doc[pi].get_objects(filter=[3])):
            try:
                _, _, _, top = obj.get_bounds()
                meta = obj.get_metadata()
                width, height = meta.width, meta.height
                if width * height > MAX_PIXELS:
                    raise ValueError("imagem grande demais")
                pil = obj.get_bitmap().to_pil()
                if pil.mode not in {"RGB", "RGBA", "L", "LA", "P", "1"}:
                    pil = pil.convert("RGB")
                buf = io.BytesIO()
                pil.save(buf, "PNG")
            except Exception:
                failed += 1
                continue
            images.append(PageImage(pi, top, buf.getvalue(), f"pagina{pi + 1}-imagem{k + 1}.png"))
    return images, failed


def split_decorative(images: list[PageImage], total_pages: int) -> tuple[list[PageImage], int]:
    """Separa imagens que se repetem em muitas páginas (logotipos, faixas) das de conteúdo."""
    pages_of: dict[str, set[int]] = defaultdict(set)
    for img in images:
        pages_of[img.sha].add(img.page)
    decorative = {
        sha for sha, pages in pages_of.items()
        if len(pages) >= DECORATIVE_MIN_PAGES and len(pages) / max(1, total_pages) >= DECORATIVE_RATIO
    }  # fmt: skip
    kept = [i for i in images if i.sha not in decorative]
    return kept, len(images) - len(kept)
