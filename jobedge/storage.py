"""SQLite storage layer for JobEdge.

The ONLY module allowed to import sqlite3. Every other module goes through
the functions here.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Sequence

_TRACKS = ("sales", "hr")

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
    best_track TEXT
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
def _connect(path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: str) -> None:
    with _connect(path) as conn:
        conn.executescript(SCHEMA)


def upsert_listings(path: str, rows: Sequence[dict]) -> int:
    """Insert new listings, ignoring duplicates by id. Returns count of NEW rows."""
    new_count = 0
    with _connect(path) as conn:
        for row in rows:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO listings
                    (id, title, company, location, url, description, source,
                     posted_at, fetched_at)
                VALUES
                    (:id, :title, :company, :location, :url, :description,
                     :source, :posted_at, :fetched_at)
                """,
                row,
            )
            if cursor.rowcount:
                new_count += 1
    return new_count


def count_unscored(path: str, profile: str) -> int:
    column = _score_column(profile)
    with _connect(path) as conn:
        cursor = conn.execute(f"SELECT COUNT(*) FROM listings WHERE {column} IS NULL")
        return cursor.fetchone()[0]


def last_fetch_time(path: str, source: str) -> str | None:
    with _connect(path) as conn:
        cursor = conn.execute(
            "SELECT MAX(finished_at) FROM cycle_log WHERE agent = ? AND status = 'ok'",
            (source,),
        )
        return cursor.fetchone()[0]


def log_cycle(
    path: str,
    agent: str,
    started_at: str,
    finished_at: str,
    records_touched: int,
    status: str,
    notes: str = "",
) -> None:
    with _connect(path) as conn:
        conn.execute(
            """
            INSERT INTO cycle_log
                (agent, started_at, finished_at, records_touched, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agent, started_at, finished_at, records_touched, status, notes),
        )


def get_listings(path: str, profile: str, limit: int = 50, min_score: int = 0) -> list[dict]:
    score_col = _score_column(profile)
    reason_col = _reason_column(profile)
    with _connect(path) as conn:
        cursor = conn.execute(
            f"""
            SELECT id, title, company, location, url, source, posted_at,
                   {score_col} AS fit_score, {reason_col} AS fit_reason, best_track
            FROM listings
            WHERE {score_col} >= ?
            ORDER BY {score_col} DESC
            LIMIT ?
            """,
            (min_score, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def _score_column(profile: str) -> str:
    if profile not in _TRACKS:
        raise ValueError(f"unknown profile {profile!r}, expected one of {_TRACKS}")
    return f"{profile}_fit_score"


def _reason_column(profile: str) -> str:
    if profile not in _TRACKS:
        raise ValueError(f"unknown profile {profile!r}, expected one of {_TRACKS}")
    return f"{profile}_fit_reason"
