"""Linha de comando: `uv run gotcha` inicia o aplicativo local em 127.0.0.1."""

from __future__ import annotations

import argparse
import os
import threading
import webbrowser
from pathlib import Path

import uvicorn

from gotcha.api.app import create_app

DEFAULT_PORT = 8765


def default_data_dir() -> Path:
    return Path(os.environ.get("GOTCHA_DATA_DIR", Path.home() / ".gotcha"))


def find_web_dist() -> Path | None:
    for candidate in (Path(__file__).resolve().parents[2] / "web" / "dist", Path("web/dist")):
        if candidate.is_dir():
            return candidate
    return None


def main() -> None:
    parser = argparse.ArgumentParser(prog="gotcha", description="Simulados de certificação.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    parser.add_argument("--no-browser", action="store_true", help="não abrir o navegador")
    args = parser.parse_args()
    app = create_app(args.data_dir, static_dir=find_web_dist())
    url = f"http://127.0.0.1:{args.port}"
    print(f"GOTCHA em {url}  (dados em {args.data_dir})")
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
