"""Garante as regras do produto no lockfile: sem IA e sem PyMuPDF (AGPL)."""

import re
from pathlib import Path

LOCK = Path(__file__).resolve().parent.parent / "uv.lock"
FORBIDDEN = {
    "openai", "anthropic", "google-generativeai", "google-genai", "langchain", "llama-index",
    "transformers", "torch", "tensorflow", "cohere", "mistralai", "ollama", "litellm",
    "pymupdf", "fitz",
}  # fmt: skip


def locked_packages() -> set[str]:
    return set(re.findall(r'(?m)^name = "([^"]+)"', LOCK.read_text(encoding="utf-8")))


def test_no_ai_or_agpl_pdf_libraries() -> None:
    found = {p.lower() for p in locked_packages()} & FORBIDDEN
    assert not found, f"Dependências proibidas pelas regras do produto: {sorted(found)}"
