"""Read/write queries for the JobEdge storage layer.

Internal to the storage package — nothing outside jobedge/storage/ should
import this directly; go through jobedge.storage instead.
"""

from __future__ import annotations

from typing import Sequence

from jobedge.storage._schema import connect, reason_column, score_column


def upsert_listings(path: str, rows: Sequence[dict]) -> int:
    """Insert new listings, ignoring duplicates by id. Returns count of NEW rows.

    A duplicate whose stored posted_at is still NULL gets backfilled from
    this fetch's parsed value -- otherwise a listing seen before the posted-
    date extraction existed (or before a source's date selector worked)
    could never pick one up, since it will never look "new" again."""
    new_count = 0
    with connect(path) as conn:
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
            elif row.get("posted_at"):
                conn.execute(
                    "UPDATE listings SET posted_at = :posted_at WHERE id = :id AND posted_at IS NULL",
                    row,
                )
    return new_count


def count_unscored(path: str, profile: str) -> int:
    column = score_column(profile)
    with connect(path) as conn:
        cursor = conn.execute(f"SELECT COUNT(*) FROM listings WHERE {column} IS NULL")
        return cursor.fetchone()[0]


def last_fetch_time(path: str, source: str) -> str | None:
    with connect(path) as conn:
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
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO cycle_log
                (agent, started_at, finished_at, records_touched, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agent, started_at, finished_at, records_touched, status, notes),
        )


def get_listings(
    path: str,
    profile: str,
    limit: int = 50,
    min_score: int = 0,
    max_age_hours: int | None = None,
) -> list[dict]:
    """max_age_hours, when set, requires a KNOWN posted_at within that window --
    a listing with no confirmed posting date is excluded rather than assumed
    fresh (steering: never silently treat unverified data as safe)."""
    score_col = score_column(profile)
    reason_col = reason_column(profile)
    age_clause = ""
    params: tuple = (min_score,)
    if max_age_hours is not None:
        age_clause = "AND posted_at IS NOT NULL AND datetime(posted_at) >= datetime('now', ?)"
        params = (min_score, f"-{max_age_hours} hours")
    with connect(path) as conn:
        cursor = conn.execute(
            f"""
            SELECT id, title, company, location, url, source, posted_at,
                   {score_col} AS fit_score, {reason_col} AS fit_reason, best_track
            FROM listings
            WHERE {score_col} >= ?
            {age_clause}
            ORDER BY {score_col} DESC
            LIMIT ?
            """,
            (*params, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_diagnostics(path: str) -> dict:
    """Read-only summary for `python -m jobedge.diagnose`. No writes."""
    with connect(path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        by_source = conn.execute(
            "SELECT source, COUNT(*) AS count FROM listings GROUP BY source ORDER BY source"
        ).fetchall()
        cross_dupes = conn.execute(
            """
            SELECT title, company, COUNT(DISTINCT source) AS source_count
            FROM listings
            WHERE title IS NOT NULL AND company IS NOT NULL
            GROUP BY title, company
            HAVING source_count > 1
            """
        ).fetchall()
        recent = conn.execute(
            "SELECT source, title, company, url, fetched_at FROM listings "
            "ORDER BY fetched_at DESC LIMIT 5"
        ).fetchall()
        quality_issues = conn.execute(
            """
            SELECT id, source, title, company, url FROM listings
            WHERE url IS NULL OR url = '' OR title IS NULL OR title = ''
               OR company IS NULL OR company = ''
            """
        ).fetchall()

    return {
        "total": total,
        "by_source": [dict(row) for row in by_source],
        "cross_source_duplicates": [dict(row) for row in cross_dupes],
        "recent": [dict(row) for row in recent],
        "quality_issues": [dict(row) for row in quality_issues],
    }
