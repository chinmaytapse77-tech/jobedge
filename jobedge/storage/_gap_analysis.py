"""Skill-gap queries for the JobEdge storage layer.

Internal to the storage package — go through jobedge.storage instead.
"""

from __future__ import annotations

from jobedge.storage._schema import connect, score_column, utcnow_iso


def get_scored_listings_below_threshold(path: str, profile: str, threshold: int) -> list[dict]:
    column = score_column(profile)
    with connect(path) as conn:
        cursor = conn.execute(
            f"""
            SELECT title, description, {column} AS fit_score
            FROM listings
            WHERE {column} IS NOT NULL AND {column} < ?
            """,
            (threshold,),
        )
        return [dict(row) for row in cursor.fetchall()]


def replace_skill_gaps(path: str, profile: str, gaps: list[tuple[str, int]]) -> None:
    """Replaces this profile's skill_gaps rows with a fresh ranking --
    gaps reflect the current pool, not an ever-growing history."""
    now = utcnow_iso()
    with connect(path) as conn:
        conn.execute("DELETE FROM skill_gaps WHERE profile = ?", (profile,))
        conn.executemany(
            "INSERT INTO skill_gaps (profile, skill, frequency, last_seen) VALUES (?, ?, ?, ?)",
            [(profile, skill, freq, now) for skill, freq in gaps],
        )


def get_skill_gaps(path: str, profile: str, limit: int = 10) -> list[dict]:
    with connect(path) as conn:
        cursor = conn.execute(
            "SELECT skill, frequency, last_seen FROM skill_gaps WHERE profile = ? "
            "ORDER BY frequency DESC LIMIT ?",
            (profile, limit),
        )
        return [dict(row) for row in cursor.fetchall()]
