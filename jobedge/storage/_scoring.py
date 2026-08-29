"""Scorer-related queries for the JobEdge storage layer.

Internal to the storage package — nothing outside jobedge/storage/ should
import this directly; go through jobedge.storage instead. Split out of
_queries.py once that file crossed the ~150-line guideline.
"""

from __future__ import annotations

from jobedge.storage._schema import connect


def get_unscored_listings(path: str, limit: int = 1000) -> list[dict]:
    """Listings missing a score for at least one profile."""
    with connect(path) as conn:
        cursor = conn.execute(
            """
            SELECT id, title, company, location, description
            FROM listings
            WHERE sales_fit_score IS NULL OR hr_fit_score IS NULL
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def update_listing_score(
    path: str,
    listing_id: str,
    sales_score: int,
    sales_reason: str,
    hr_score: int,
    hr_reason: str,
    best_track: str | None,
    experience_ok: bool | None = None,
) -> None:
    with connect(path) as conn:
        conn.execute(
            """
            UPDATE listings
            SET sales_fit_score = ?, sales_fit_reason = ?,
                hr_fit_score = ?, hr_fit_reason = ?, best_track = ?,
                experience_ok = ?
            WHERE id = ?
            """,
            (
                sales_score,
                sales_reason,
                hr_score,
                hr_reason,
                best_track,
                None if experience_ok is None else int(experience_ok),
                listing_id,
            ),
        )
