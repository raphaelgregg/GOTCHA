"""Conexão SQLite com esquema e utilitários de JSON, compartilhada pelos repositórios."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS exams (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS batches (
  id TEXT PRIMARY KEY, filename TEXT NOT NULL, format TEXT NOT NULL, title TEXT NOT NULL,
  status TEXT NOT NULL, exam_id TEXT, created_at REAL NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cases (
  id TEXT PRIMARY KEY, exam_id TEXT NOT NULL, batch_id TEXT, title TEXT, text TEXT NOT NULL,
  data TEXT);
CREATE TABLE IF NOT EXISTS questions (
  id TEXT PRIMARY KEY, exam_id TEXT NOT NULL, batch_id TEXT, topic INTEGER NOT NULL,
  number INTEGER NOT NULL, data TEXT NOT NULL, fingerprint TEXT,
  UNIQUE (exam_id, topic, number));
CREATE TABLE IF NOT EXISTS assets (
  sha TEXT PRIMARY KEY, data BLOB NOT NULL, mime TEXT, width INTEGER, height INTEGER,
  pages INTEGER, size INTEGER, view_data BLOB, names TEXT, origin TEXT, conversion TEXT,
  default_alt TEXT);
CREATE TABLE IF NOT EXISTS asset_refs (owner TEXT NOT NULL, sha TEXT NOT NULL, PRIMARY KEY (owner, sha));
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, spec TEXT NOT NULL, created_at REAL NOT NULL, finished_at REAL,
  question_ids TEXT NOT NULL, responses TEXT NOT NULL, marks TEXT NOT NULL,
  elapsed_before REAL NOT NULL, resumed_at REAL, limit_seconds INTEGER, result TEXT);
CREATE TABLE IF NOT EXISTS question_stats (
  question_id TEXT PRIMARY KEY, last_outcome TEXT, marked INTEGER NOT NULL DEFAULT 0);
"""


class Database:
    def __init__(self, path: Path | str) -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA)
        self._upgrade()

    def _upgrade(self) -> None:
        """Bancos criados por versões anteriores ganham as colunas novas."""
        wanted = {
            "assets": {
                "mime": "TEXT", "width": "INTEGER", "height": "INTEGER", "pages": "INTEGER",
                "size": "INTEGER", "view_data": "BLOB", "names": "TEXT", "origin": "TEXT",
                "conversion": "TEXT", "default_alt": "TEXT",
            },
            "cases": {"data": "TEXT"},
            "questions": {"fingerprint": "TEXT"},
        }  # fmt: skip
        for table, columns in wanted.items():
            have = {r["name"] for r in self._conn.execute(f"PRAGMA table_info({table})")}
            for name, decl in columns.items():
                if name not in have:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, params)

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                yield
            except BaseException:
                self._conn.execute("ROLLBACK")
                raise
            else:
                self._conn.execute("COMMIT")
