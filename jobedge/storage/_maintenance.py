"""One-off maintenance queries for the JobEdge storage layer.

Internal to the storage package — go through jobedge.storage instead.
"""

from __future__ import annotations

from typing import Callable

from jobedge.storage._schema import connect


def backfill_job_bank_text(path: str, strip_label: Callable[[str | None, str], str | None]) -> int:
    """Re-applies strip_label to already-stored job_bank title/location
    values -- rows fetched before the selector fix landed still carry the
    old corrupted text (dedup means they're never reprocessed on their
    own). Already-clean rows are left untouched. Returns rows updated."""
    with connect(path) as conn:
        rows = conn.execute("SELECT id, title, location FROM listings WHERE source = 'job_bank'").fetchall()
        updated = 0
        for row in rows:
            new_title = strip_label(row["title"], "Job Bank")
            new_location = strip_label(row["location"], "Location")
            if new_title != row["title"] or new_location != row["location"]:
                conn.execute(
                    "UPDATE listings SET title = ?, location = ? WHERE id = ?",
                    (new_title, new_location, row["id"]),
                )
                updated += 1
        return updated
