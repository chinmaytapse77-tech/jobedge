"""Shared "posted X ago" / absolute-date parsing for HTML-scraping Sources.

Only matches unambiguous patterns (an explicit number + time unit, "today",
"yesterday", or a real calendar date) -- never a bare word like "new", which
shows up in unrelated contexts (job titles, badges) far too often to trust
as a freshness signal.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

_RELATIVE_RE = re.compile(
    r"\b(\d+)\s*(minute|hour|day|week)s?\s*(?:ago)?\b", re.IGNORECASE
)
_TODAY_RE = re.compile(r"\b(today|just posted|just now)\b", re.IGNORECASE)
_YESTERDAY_RE = re.compile(r"\byesterday\b", re.IGNORECASE)

_MONTHS = {
    name: i
    for i, names in enumerate(
        [
            ("january", "jan", "janvier"),
            ("february", "feb", "février", "fevrier"),
            ("march", "mar", "mars"),
            ("april", "apr", "avril"),
            ("may", "mai"),
            ("june", "jun", "juin"),
            ("july", "jul", "juillet"),
            ("august", "aug", "août", "aout"),
            ("september", "sep", "sept", "septembre"),
            ("october", "oct", "octobre"),
            ("november", "nov", "novembre"),
            ("december", "dec", "décembre", "decembre"),
        ],
        start=1,
    )
    for name in names
}
_MONTH_NAME = "|".join(sorted(_MONTHS, key=len, reverse=True))
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTH_DAY_YEAR_RE = re.compile(
    rf"\b({_MONTH_NAME})\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.IGNORECASE
)
_DAY_MONTH_YEAR_RE = re.compile(
    rf"\b(\d{{1,2}})\s+({_MONTH_NAME})\.?,?\s+(\d{{4}})\b", re.IGNORECASE
)


def parse_posted_at(text: str | None, reference: datetime | None = None) -> str | None:
    """Best-effort extraction of a posting date/time from free text.
    Returns an ISO 8601 UTC string, or None if nothing unambiguous is found."""
    if not text:
        return None
    now = reference or datetime.now(timezone.utc)

    match = _RELATIVE_RE.search(text)
    if match:
        amount, unit = int(match.group(1)), match.group(2).lower()
        delta = {
            "minute": timedelta(minutes=amount),
            "hour": timedelta(hours=amount),
            "day": timedelta(days=amount),
            "week": timedelta(weeks=amount),
        }[unit]
        return (now - delta).isoformat()

    if _TODAY_RE.search(text):
        return now.isoformat()
    if _YESTERDAY_RE.search(text):
        return (now - timedelta(days=1)).isoformat()

    match = _ISO_DATE_RE.search(text)
    if match:
        year, month, day = (int(g) for g in match.groups())
        return _safe_date(year, month, day)

    match = _MONTH_DAY_YEAR_RE.search(text)
    if match:
        month = _MONTHS.get(match.group(1).lower())
        if month:
            return _safe_date(int(match.group(3)), month, int(match.group(2)))

    match = _DAY_MONTH_YEAR_RE.search(text)
    if match:
        month = _MONTHS.get(match.group(2).lower())
        if month:
            return _safe_date(int(match.group(3)), month, int(match.group(1)))

    return None


def _safe_date(year: int, month: int, day: int) -> str | None:
    try:
        return datetime(year, month, day, tzinfo=timezone.utc).isoformat()
    except ValueError:
        return None
