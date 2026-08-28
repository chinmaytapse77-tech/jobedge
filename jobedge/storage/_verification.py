"""Verifier-related queries for the JobEdge storage layer.

Internal to the storage package — go through jobedge.storage instead.
"""

from __future__ import annotations

from jobedge.storage._schema import connect, reason_column, score_column


def get_recent_agent_notes(path: str, agent: str, limit: int = 2) -> list[str]:
    with connect(path) as conn:
        cursor = conn.execute(
            "SELECT notes FROM cycle_log WHERE agent = ? AND status = 'ok' "
            "ORDER BY started_at DESC LIMIT ?",
            (agent, limit),
        )
        return [row[0] for row in cursor.fetchall()]


def get_all_scores(path: str, profile: str) -> list[int]:
    column = score_column(profile)
    with connect(path) as conn:
        cursor = conn.execute(f"SELECT {column} FROM listings WHERE {column} IS NOT NULL")
        return [row[0] for row in cursor.fetchall()]


def reset_profile_scores(path: str, profile: str) -> int:
    """Clears this profile's scores so the Scorer reprocesses everything
    next cycle. Returns how many rows were reset."""
    score_col = score_column(profile)
    reason_col = reason_column(profile)
    with connect(path) as conn:
        cursor = conn.execute(
            f"UPDATE listings SET {score_col} = NULL, {reason_col} = NULL, best_track = NULL "
            f"WHERE {score_col} IS NOT NULL"
        )
        return cursor.rowcount
