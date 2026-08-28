"""Pure skill-gap logic: for one profile, which of its market_skills
(skills relevant to the role that aren't already in my_skills) would
unlock the most listings if the candidate had them. No storage, no I/O.
"""

from __future__ import annotations

from collections import Counter

from jobedge.config import Profile
from jobedge.scoring import SKILL_POINTS

TOP_N = 10


def missing_skills(profile: Profile) -> list[str]:
    have = {skill.lower() for skill in profile.my_skills}
    return [skill for skill in profile.market_skills if skill.lower() not in have]


def rank_skill_gaps(
    profile: Profile, min_fit_score: int, below_threshold_listings: list[dict]
) -> list[tuple[str, int]]:
    """Returns [(skill, unlock_count), ...] sorted by unlock_count desc,
    top TOP_N. A skill "unlocks" a listing if that listing mentions it and
    adding SKILL_POINTS would push the listing's score to/above
    min_fit_score."""
    candidates = missing_skills(profile)
    if not candidates:
        return []

    counts: Counter[str] = Counter()
    for listing in below_threshold_listings:
        haystack = " ".join(filter(None, [listing.get("title"), listing.get("description")])).lower()
        score = listing.get("fit_score") or 0
        for skill in candidates:
            if skill.lower() in haystack and score + SKILL_POINTS >= min_fit_score:
                counts[skill] += 1

    return counts.most_common(TOP_N)
