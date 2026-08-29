"""Best-effort experience-level signal detection for listing text.

Generic English hiring-language patterns (senior/junior words, "X years
experience" phrasing) -- not resume- or role-specific, so these live here
as code rather than config.yaml, same precedent as the relative-date words
in jobedge/sources/dateparse.py. The acceptable ceiling itself IS
config-driven (Config.max_years_experience), since that's a job-search
preference, not a language pattern.

Absence of any signal is treated as fine, never excluded -- most postings
never state a required years figure, and hiding them by default would
throw away perfectly good entry-level-friendly listings.
"""

from __future__ import annotations

import re

# Deliberately excludes words that collide with this project's own target
# titles ("executive", "manager", "lead") -- see config.yaml's sales/hr
# target_titles (e.g. "Account Executive", "Territory Sales Manager").
SENIOR_SIGNALS = (
    "senior",
    "sr.",
    "principal",
    "director",
    "head of",
    "vp ",
    "vice president",
    "chief ",
)

ENTRY_SIGNALS = (
    "entry level",
    "entry-level",
    "junior",
    "jr.",
    "new grad",
    "recent graduate",
    "no experience necessary",
    "no experience required",
)

_YEARS_RE = re.compile(
    r"\b(\d+)\+?\s*(?:-|to)?\s*\d*\+?\s*years?\s*(?:of\s+)?(?:related\s+|relevant\s+)?experience\b",
    re.IGNORECASE,
)


def extract_years_required(text: str | None) -> int | None:
    """Lower bound of the first "X (to Y) years (of) experience" phrase
    found, or None if the text states no explicit figure."""
    if not text:
        return None
    match = _YEARS_RE.search(text)
    return int(match.group(1)) if match else None


def is_within_experience_range(
    title: str | None, description: str | None, max_years: int
) -> bool:
    """True unless the listing clearly asks for more experience than
    max_years -- an explicit senior title/keyword, or a stated years
    figure above the ceiling. Everything else (including no signal at
    all) passes."""
    haystack = " ".join(filter(None, [title, description])).lower()
    if any(signal in haystack for signal in ENTRY_SIGNALS):
        return True
    if any(signal in haystack for signal in SENIOR_SIGNALS):
        return False
    years = extract_years_required(haystack)
    if years is not None and years > max_years:
        return False
    return True
