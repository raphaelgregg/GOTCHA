"""Propriedades: nenhum importador deve quebrar de forma inesperada com entrada arbitrária."""

import contextlib

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gotcha.importers import Source, UnsupportedFormat, detect
from gotcha.importers.bundle import BundleError, load_source

FAST = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
EXPECTED = (ValueError, UnsupportedFormat, BundleError)


@FAST
@given(st.binary(max_size=2000))
def test_arbitrary_bytes_are_refused_cleanly_or_parsed(data: bytes) -> None:
    with contextlib.suppress(*EXPECTED):
        src = load_source("x.bin", data)
        detect(src).parse(src)


@FAST
@given(st.text(max_size=1500))
def test_arbitrary_text_never_crashes_text_importers(text: str) -> None:
    for prefix in ("", "Q1\n", "Question #1\n", "numero,pergunta,A,B,resposta\n1,"):
        src = Source(filename="x.txt", data=(prefix + text).encode("utf-8", "replace"))
        with contextlib.suppress(*EXPECTED):
            detect(src).parse(src)
