"""Recursos de mídia: tipo detectado pelo conteúdo, dimensões, SHA-256 e SVG sanitizado.

Os bytes originais são sempre preservados. A única transformação é o SVG sanitizado, que vira uma
versão de exibição separada (`view_data`); o original nunca é exibido.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass

from lxml import etree
from PIL import Image, UnidentifiedImageError

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 100_000_000
SVG_NS = "http://www.w3.org/2000/svg"


class AssetError(ValueError):
    """Recurso recusado (tipo não permitido, corrompido ou acima dos limites)."""


@dataclass(frozen=True)
class AssetInfo:
    sha: str
    mime: str
    width: int | None
    height: int | None
    pages: int | None
    size: int
    view_data: bytes | None  # só quando a versão exibível difere do original (SVG)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sniff_mime(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    head = data.lstrip(b"\xef\xbb\xbf \t\r\n")[:2048]
    if head.startswith((b"<svg", b"<?xml")) and b"<svg" in head:
        return "image/svg+xml"
    return None


_ALLOWED_TAGS = {
    "svg", "g", "defs", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text",
    "tspan", "title", "desc", "lineargradient", "radialgradient", "stop", "clippath", "mask",
}  # fmt: skip
_ALLOWED_ATTRS = {
    "id", "class", "d", "x", "y", "cx", "cy", "r", "rx", "ry", "x1", "x2", "y1", "y2", "points",
    "width", "height", "viewbox", "fill", "stroke", "stroke-width", "stroke-linecap",
    "stroke-linejoin", "stroke-dasharray", "opacity", "fill-opacity", "stroke-opacity", "transform",
    "font-size", "font-family", "font-weight", "text-anchor", "offset", "stop-color", "stop-opacity",
    "gradientunits", "gradienttransform", "preserveaspectratio", "version", "fill-rule", "clip-path",
    "mask", "dx", "dy",
}  # fmt: skip


def _safe_value(value: str) -> bool:
    low = value.lower()
    if "javascript:" in low or "data:" in low or "expression(" in low:
        return False
    return not any(not part.startswith("#") for part in re.findall(r"url\(\s*['\"]?([^)'\"]*)", low))


def sanitize_svg(data: bytes) -> bytes:
    if b"<!ENTITY" in data or b"<!entity" in data:
        raise AssetError("SVG com declaração de entidades não é aceito.")
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        remove_comments=True,
        remove_pis=True,
        huge_tree=False,
    )
    try:
        root = etree.fromstring(data, parser)
    except etree.XMLSyntaxError as exc:
        raise AssetError(f"SVG inválido: {exc}") from exc
    if etree.QName(root).localname.lower() != "svg":
        raise AssetError("O arquivo não é um SVG.")
    for el in list(root.iter()):
        if el is root or el.getparent() is None:
            continue
        q = etree.QName(el)
        if q.namespace not in (None, SVG_NS) or q.localname.lower() not in _ALLOWED_TAGS:
            parent = el.getparent()
            if parent is not None:
                if el.tail:  # preserva o texto que vem depois do elemento removido
                    prev = el.getprevious()
                    if prev is not None:
                        prev.tail = (prev.tail or "") + el.tail
                    else:
                        parent.text = (parent.text or "") + el.tail
                parent.remove(el)
    for el in root.iter():
        for name in list(el.attrib):
            local = etree.QName(name).localname.lower()
            value = str(el.attrib[name])
            if (
                local not in _ALLOWED_ATTRS
                or local.startswith("on")
                or (etree.QName(name).namespace not in (None, SVG_NS))
                or not _safe_value(value)
            ):
                del el.attrib[name]
    return bytes(etree.tostring(root))


def _num(value: str | None) -> int | None:
    m = re.match(r"^\s*([0-9.]+)", value or "")
    return round(float(m.group(1))) if m else None


def _svg_dims(svg: bytes) -> tuple[int | None, int | None]:
    root = etree.fromstring(svg)
    w, h = _num(root.get("width")), _num(root.get("height"))
    if (w is None or h is None) and root.get("viewBox"):
        parts = root.get("viewBox", "").replace(",", " ").split()
        if len(parts) == 4:
            w, h = w or round(float(parts[2])), h or round(float(parts[3]))
    return w, h


def _raster(data: bytes, mime: str, max_pixels: int) -> tuple[int, int]:
    try:
        with Image.open(io.BytesIO(data)) as img:
            w, h = img.size
            if w * h > max_pixels:
                raise AssetError(f"Imagem com {w * h} pixels excede o limite de {max_pixels}.")
            img.load()  # detecta arquivo truncado ou corrompido
            return w, h
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise AssetError(f"Imagem inválida ou corrompida ({mime}): {exc}") from exc


def analyze(data: bytes, max_bytes: int = MAX_BYTES, max_pixels: int = MAX_PIXELS) -> AssetInfo:
    if len(data) > max_bytes:
        raise AssetError("O recurso excede o limite de tamanho.")
    mime = sniff_mime(data)
    if mime is None:
        raise AssetError("Tipo de recurso não permitido (aceitos: PNG, JPEG, WebP, GIF, SVG e PDF).")
    sha = sha256_hex(data)
    if mime == "image/svg+xml":
        view = sanitize_svg(data)
        w, h = _svg_dims(view)
        return AssetInfo(sha, mime, w, h, None, len(data), view)
    if mime == "application/pdf":
        import pypdfium2 as pdfium

        try:
            doc = pdfium.PdfDocument(data)
            page_w, page_h = doc[0].get_size() if len(doc) else (0, 0)
            return AssetInfo(sha, mime, round(page_w), round(page_h), len(doc), len(data), None)
        except Exception as exc:
            raise AssetError(f"PDF inválido: {exc}") from exc
    w, h = _raster(data, mime, max_pixels)
    return AssetInfo(sha, mime, w, h, None, len(data), None)
