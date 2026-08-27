"""Pure scoring logic: how well one listing fits one profile.

No storage, no I/O -- easy to test in isolation. The Scorer agent
(jobedge/agents/scorer.py) is the only caller.
"""

from __future__ import annotations

from jobedge.config import Profile

TITLE_MATCH_POINTS = 40
KEYWORD_POINTS = 6
SKILL_POINTS = 4
MAX_KEYWORD_MATCHES = 6
MAX_SKILL_MATCHES = 6
MAX_SCORE = 100

QUEBEC_MARKERS = ("qc", "québec", "quebec")


def score_listing(
    profile: Profile, title: str | None, description: str | None, location: str | None
) -> tuple[int, str]:
    """Returns (score 0-100, human-readable reason)."""
    haystack = " ".join(filter(None, [title, description])).lower()
    is_quebec = bool(location) and any(marker in location.lower() for marker in QUEBEC_MARKERS)

    score = 0
    reasons: list[str] = []

    title_hit = _first_match((title or "").lower(), profile.target_titles)
    if title_hit:
        score += TITLE_MATCH_POINTS
        reasons.append(f"title matches '{title_hit}'")

    keywords = list(profile.keywords) + (list(profile.keywords_fr) if is_quebec else [])
    keyword_hits = _all_matches(haystack, keywords)[:MAX_KEYWORD_MATCHES]
    if keyword_hits:
        score += len(keyword_hits) * KEYWORD_POINTS
        reasons.append(f"keywords found: {', '.join(keyword_hits)}")

    skill_hits = _all_matches(haystack, profile.my_skills)[:MAX_SKILL_MATCHES]
    if skill_hits:
        score += len(skill_hits) * SKILL_POINTS
        reasons.append(f"{len(skill_hits)} of your skills mentioned: {', '.join(skill_hits)}")

    score = min(score, MAX_SCORE)
    reason = "; ".join(reasons) if reasons else "no title/keyword/skill overlap found"
    return score, reason


def _first_match(haystack: str, candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate.lower() in haystack:
            return candidate
    return None


def _all_matches(haystack: str, candidates: list[str]) -> list[str]:
    return [candidate for candidate in candidates if candidate.lower() in haystack]
