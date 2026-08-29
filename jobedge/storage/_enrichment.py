"""Enrichment-related queries for the JobEdge storage layer.

Internal to the storage package — go through jobedge.storage instead.
"""

from __future__ import annotations

from jobedge.storage._schema import connect


def get_enrichment_candidates(path: str, min_score: int, limit: int) -> list[dict]:
    """Highest-scoring listings (by either profile) still missing a
    description -- these are worth the extra request to fetch their full
    posting page and rescore with real text."""
    with connect(path) as conn:
        cursor = conn.execute(
            """
            SELECT id, url, source, title, location
            FROM listings
            WHERE description IS NULL
              AND (sales_fit_score >= ? OR hr_fit_score >= ?)
            ORDER BY MAX(sales_fit_score, hr_fit_score) DESC
            LIMIT ?
            """,
            (min_score, min_score, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def update_listing_description(
    path: str, listing_id: str, description: str, posted_at: str | None = None
) -> None:
    """posted_at, when given, only fills a currently-NULL value -- a search
    card's own date (already stored) is never overwritten by a detail-page
    guess."""
    with connect(path) as conn:
        conn.execute("UPDATE listings SET description = ? WHERE id = ?", (description, listing_id))
        if posted_at:
            conn.execute(
                "UPDATE listings SET posted_at = ? WHERE id = ? AND posted_at IS NULL",
                (posted_at, listing_id),
            )
