"""Imagens sintéticas para os testes."""

import io

from PIL import Image


def png(w: int = 40, h: int = 20, color: str = "red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


def jpeg(w: int = 30, h: int = 30) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "blue").save(buf, "JPEG")
    return buf.getvalue()


def webp(w: int = 16, h: int = 16) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "green").save(buf, "WEBP")
    return buf.getvalue()


def gif(w: int = 8, h: int = 8) -> bytes:
    buf = io.BytesIO()
    Image.new("P", (w, h)).save(buf, "GIF")
    return buf.getvalue()


SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50" viewBox="0 0 100 50">'
    b'<rect x="1" y="1" width="20" height="10" fill="red"/><circle cx="50" cy="25" r="10"/></svg>'
)
SVG_EVIL = (
    b'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'
    b' width="100" height="50" onload="alert(1)">'
    b"<script>alert(1)</script><foreignObject><div>x</div></foreignObject>"
    b"<style>@import url(http://evil/x.css)</style>"
    b'<a xlink:href="javascript:alert(1)"><rect width="5" height="5" onclick="x()"/></a>'
    b'<use xlink:href="http://evil/x.svg#a"/><image href="http://evil/x.png"/>'
    b'<rect id="ok" x="0" y="0" width="10" height="10" fill="url(http://evil/g)" stroke="black"/></svg>'
)
