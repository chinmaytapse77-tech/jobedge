"""Schema, connection, and id helpers for the JobEdge storage layer.

Internal to the storage package — nothing outside jobedge/storage/ should
import this directly; go through jobedge.storage instead.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

TRACKS = ("sales", "hr")

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    url TEXT,
    description TEXT,
    source TEXT NOT NULL,
    posted_at TEXT,
    fetched_at TEXT NOT NULL,
    sales_fit_score INTEGER,
    sales_fit_reason TEXT,
    hr_fit_score INTEGER,
    hr_fit_reason TEXT,
    best_track TEXT,
    experience_ok INTEGER
);

CREATE TABLE IF NOT EXISTS skill_gaps (
    profile TEXT NOT NULL,
    skill TEXT NOT NULL,
    frequency INTEGER NOT NULL,
    last_seen TEXT NOT NULL,
    PRIMARY KEY (profile, skill)
);

CREATE TABLE IF NOT EXISTS cycle_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    records_touched INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    notes TEXT
);
"""


def make_listing_id(source: str, url: str) -> str:
    """Stable dedup key: hash of source + url."""
    return hashlib.sha256(f"{source}|{url}".encode("utf-8")).hexdigest()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect(path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: str) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        _migrate_columns(conn)


def _migrate_columns(conn: sqlite3.Connection) -> None:
    """CREATE TABLE IF NOT EXISTS never adds columns to an already-existing
    table -- a column added to SCHEMA after the production db was created
    needs an explicit ALTER TABLE, guarded so it only runs once."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(listings)")}
    if "experience_ok" not in existing:
        conn.execute("ALTER TABLE listings ADD COLUMN experience_ok INTEGER")


def score_column(profile: str) -> str:
    if profile not in TRACKS:
        raise ValueError(f"unknown profile {profile!r}, expected one of {TRACKS}")
    return f"{profile}_fit_score"


def reason_column(profile: str) -> str:
    if profile not in TRACKS:
        raise ValueError(f"unknown profile {profile!r}, expected one of {TRACKS}")
    return f"{profile}_fit_reason"
