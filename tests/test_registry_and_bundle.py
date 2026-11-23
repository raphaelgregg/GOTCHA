import io
import zipfile

import pytest

from gotcha.importers.base import ProtectedFormat, Source, UnsupportedFormat, detect
from gotcha.importers.bundle import BundleError, load_source
from tests.html_fixture import card, page


def test_detect_picks_importer_by_content() -> None:
    importer = detect(
        Source(filename="sem_extensao", data=page(card(1, choices=["a", "b"], answer="A")))
    )
    assert importer.name == "html"


def test_vce_is_recognised_and_refused_with_guidance() -> None:
    data = bytes.fromhex("85a80304") + b"\x00" * 200
    with pytest.raises(ProtectedFormat) as exc:
        detect(Source(filename="exam.vce", data=data))
    assert "PDF" in str(exc.value)


def test_unknown_format_is_refused() -> None:
    with pytest.raises(UnsupportedFormat):
        detect(Source(filename="x.bin", data=b"\x00\x01\x02 nada reconhecivel"))


def zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in members.items():
            z.writestr(name, content)
    return buf.getvalue()


def test_zip_bundle_loads_main_file_and_images() -> None:
    html = page(card(1, answer_img="r.png"))
    z = zip_bytes({"pagina.html": html, "pagina_files/r.png": b"\x89PNG-data"})
    src = load_source("pacote.zip", z)
    assert src.filename == "pagina.html" and src.data == html
    assert src.assets["r.png"] == b"\x89PNG-data"


def test_plain_file_is_returned_unchanged() -> None:
    src = load_source("a.txt", b"conteudo")
    assert src.filename == "a.txt" and src.data == b"conteudo" and src.assets == {}


def test_zip_path_traversal_members_are_ignored() -> None:
    z = zip_bytes({"p.html": page(card(1)), "../../evil.png": b"x"})
    assert "evil.png" not in load_source("p.zip", z).assets


def test_zip_without_supported_file_is_refused() -> None:
    with pytest.raises(BundleError, match="arquivo"):
        load_source("p.zip", zip_bytes({"leiame.md": b"oi"}))


def test_zip_bomb_is_refused() -> None:
    z = zip_bytes({"p.html": page(card(1)), "grande.png": b"0" * (3 * 1024 * 1024)})
    with pytest.raises(BundleError, match="limite"):
        load_source("p.zip", z, max_total_bytes=1024 * 1024)
