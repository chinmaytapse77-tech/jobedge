"""One-off maintenance queries for the JobEdge storage layer.

Internal to the storage package — go through jobedge.storage instead.
"""

from __future__ import annotations

from typing import Callable

from jobedge.storage._schema import connect


def backfill_experience_ok(
    path: str, max_years: int, is_within_range: Callable[[str | None, str | None, int], bool]
) -> int:
    """Computes experience_ok for every listing missing it -- almost all
    already-scored rows, since the Scorer only ever looks at unscored ones
    and this column didn't exist when they were first scored. Returns rows
    updated."""
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT id, title, description FROM listings WHERE experience_ok IS NULL"
        ).fetchall()
        for row in rows:
            experience_ok = int(is_within_range(row["title"], row["description"], max_years))
            conn.execute(
                "UPDATE listings SET experience_ok = ? WHERE id = ?", (experience_ok, row["id"])
            )
        return len(rows)


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
