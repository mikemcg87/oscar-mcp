"""Read-only access to OSCAR's SQLite database.

OSCAR 2.x keeps every profile's data in a single `oscar.db`. This module finds
that file and opens it strictly read-only, so an MCP client can never modify a
user's therapy data by accident.
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

#: Where OSCAR 2.x puts its data by default, per platform. The first existing
#: file wins when OSCAR_DB_PATH is not set.
DEFAULT_DB_NAMES = ("OSCAR20_Data/oscar.db", "OSCAR_Data/oscar.db")


class OscarNotFound(RuntimeError):
    """No OSCAR database could be located."""


def find_db(explicit: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the oscar.db path.

    Order: an explicit path, then $OSCAR_DB_PATH, then the usual Documents
    locations. Raises OscarNotFound with actionable guidance if nothing exists.
    """
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env = os.environ.get("OSCAR_DB_PATH")
    if env:
        candidates.append(Path(env).expanduser())
    docs = Path.home() / "Documents"
    candidates.extend(docs / name for name in DEFAULT_DB_NAMES)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    tried = "\n  ".join(str(c) for c in candidates)
    raise OscarNotFound(
        "Could not find oscar.db. Set OSCAR_DB_PATH to its full path. Tried:\n  " + tried
    )


@dataclass(frozen=True)
class Database:
    """A read-only handle to an OSCAR database."""

    path: Path

    @classmethod
    def open(cls, explicit: str | os.PathLike[str] | None = None) -> "Database":
        return cls(path=find_db(explicit))

    def connect(self) -> sqlite3.Connection:
        # `mode=ro` makes SQLite refuse any write, even a stray one.
        uri = f"file:{self.path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(sql, params).fetchall()

    def active_profile_id(self) -> int | None:
        rows = self.query("SELECT id FROM profiles WHERE status = 'active' ORDER BY id LIMIT 1")
        if rows:
            return rows[0]["id"]
        rows = self.query("SELECT id FROM profiles ORDER BY id LIMIT 1")
        return rows[0]["id"] if rows else None
