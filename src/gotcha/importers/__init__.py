"""Importadores. Importar este pacote registra todos os formatos suportados."""

from . import html_saved, json_app, pdf, tabular, txt  # noqa: F401
from .base import ProtectedFormat, Source, UnsupportedFormat, detect, get, names

__all__ = ["ProtectedFormat", "Source", "UnsupportedFormat", "detect", "get", "names"]
