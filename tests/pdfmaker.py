"""Gera PDFs mínimos com texto para os testes (sem dependências extras)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


Image = tuple[float, float, float, float, tuple[int, int, int]]  # x, y, largura, altura, cor RGB


def make_pdf(pages: list[list[str]], images: Mapping[int, Sequence[Image]] | None = None) -> bytes:
    """PDF mínimo com texto (uma linha a cada 12 pt, a partir de y=800) e imagens sólidas posicionadas."""
    images = images or {}
    objs: list[bytes] = []
    n_pages = len(pages)
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n_pages))
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    base = 4 + 2 * n_pages  # os objetos de imagem vêm depois das páginas
    image_ids: dict[tuple[int, int, int], int] = {}
    for placed in images.values():
        for *_, color in placed:
            image_ids.setdefault(color, base + len(image_ids))
    for i, lines in enumerate(pages):
        content_id = 5 + 2 * i
        names = {c: f"/I{image_ids[c] - base}" for *_, c in images.get(i, [])}
        xobjects = " ".join(f"{n} {image_ids[c]} 0 R" for c, n in names.items())
        objs.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << "
                f"/Font << /F1 3 0 R >> /XObject << {xobjects} >> >> /Contents {content_id} 0 R >>"
            ).encode()
        )
        ops = []
        for x, y, w, h, color in images.get(i, []):
            ops.append(f"q {w} 0 0 {h} {x} {y} cm {names[color]} Do Q")
        ops += ["BT", "/F1 10 Tf", "12 TL", "40 800 Td"]
        for line in lines:
            ops.append(f"({_esc(line)}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("latin-1", "replace")
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    for color in sorted(image_ids, key=image_ids.get):  # type: ignore[arg-type]
        raw = bytes(color) * 4  # 2x2 pixels RGB
        objs.append(
            b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceRGB "
            b"/BitsPerComponent 8 /Length %d >>\nstream\n" % len(raw) + raw + b"\nendstream"
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
