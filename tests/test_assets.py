"""Recursos: tipo por conteúdo, dimensões, SHA-256, SVG sanitizado e limites."""

import pytest

from gotcha.qtypes.assets import AssetError, analyze, sanitize_svg, sha256_hex
from tests import imgs


@pytest.mark.parametrize(
    ("data", "mime", "size"),
    [
        (imgs.png(40, 20), "image/png", (40, 20)),
        (imgs.jpeg(30, 30), "image/jpeg", (30, 30)),
        (imgs.webp(16, 16), "image/webp", (16, 16)),
        (imgs.gif(8, 8), "image/gif", (8, 8)),
    ],
)
def test_raster_images_are_identified_by_content_with_dimensions(
    data: bytes, mime: str, size: tuple[int, int]
) -> None:
    info = analyze(data)
    assert info.mime == mime and (info.width, info.height) == size
    assert info.sha == sha256_hex(data) and info.size == len(data)


def test_extension_is_irrelevant() -> None:
    assert analyze(imgs.png()).mime == "image/png"  # nenhum nome é usado


def test_svg_dimensions_and_sanitized_view() -> None:
    info = analyze(imgs.SVG)
    assert info.mime == "image/svg+xml" and (info.width, info.height) == (100, 50)
    assert info.view_data is not None and b"<rect" in info.view_data


def test_png_view_is_the_original_bytes_untouched() -> None:
    data = imgs.png()
    assert analyze(data).view_data is None  # nada é recomprimido nem alterado


def test_svg_sanitizer_removes_scripts_events_external_refs_and_styles() -> None:
    clean = sanitize_svg(imgs.SVG_EVIL).decode()
    for forbidden in (
        "script",
        "onload",
        "onclick",
        "foreignObject",
        "javascript",
        "evil",
        "<style",
        "<use",
        "<image",
        "href",
    ):
        assert forbidden not in clean, forbidden
    assert 'id="ok"' in clean and "<rect" in clean


def test_svg_with_entities_is_refused() -> None:
    bomb = b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaa">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>'
    with pytest.raises(AssetError):
        sanitize_svg(bomb)


def test_pdf_attachment_reports_pages() -> None:
    from tests.pdfmaker import make_pdf

    info = analyze(make_pdf([["a"], ["b"]]))
    assert info.mime == "application/pdf" and info.pages == 2


@pytest.mark.parametrize("data", [b"", b"texto qualquer", b"MZ\x90\x00executavel", b"<html></html>"])
def test_unsupported_content_is_refused(data: bytes) -> None:
    with pytest.raises(AssetError):
        analyze(data)


def test_size_limit() -> None:
    with pytest.raises(AssetError, match="limite"):
        analyze(imgs.png(), max_bytes=10)


def test_decompression_bomb_is_refused() -> None:
    with pytest.raises(AssetError, match="pixels"):
        analyze(imgs.png(400, 400), max_pixels=1000)


def test_corrupted_image_is_refused() -> None:
    with pytest.raises(AssetError):
        analyze(imgs.png()[:40])
