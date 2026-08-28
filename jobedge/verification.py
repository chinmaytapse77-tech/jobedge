"""Pure verification logic: detect degenerate scoring and silently-dead
sources. No storage, no I/O.
"""

from __future__ import annotations

HIGH_SCORE_THRESHOLD = 90
HIGH_SCORE_FRACTION = 0.8
MIN_SCORED_FOR_CHECK = 5


def is_scoring_degenerate(scores: list[int]) -> bool:
    """True if scoring looks broken: almost everything crammed near the
    top of the range. Everything-at-0 is normal (nothing matched yet),
    so that alone is never flagged."""
    if len(scores) < MIN_SCORED_FOR_CHECK:
        return False
    high = sum(1 for score in scores if score > HIGH_SCORE_THRESHOLD)
    return high / len(scores) >= HIGH_SCORE_FRACTION


def is_source_silent(recent_notes: list[str]) -> bool:
    """True if a registered source's last runs all report zero rows
    fetched -- likely blocked, not "no jobs today". Relies on the
    "N rows (M new)" format every real Fetcher's AgentResult.notes uses."""
    if not recent_notes:
        return False
    return all(note.startswith("0 rows") for note in recent_notes)
