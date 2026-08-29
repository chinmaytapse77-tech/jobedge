"""Shared adaptive-search pattern for HTML-scraping Sources.

Searches every configured location with EVERY profile target title
separately (not just the primary one) -- a listing titled "Sales
Representative" or "Recruiter" is a real, distinct search on Job Bank/
Eluta from "B2B Sales Executive"; searching only the first title missed
whole categories of relevant roles even though the Scorer would have
matched them fine once found. If a location still comes up short,
relaxes to a location-only search and logs that it did, rather than
silently returning a near-empty database (steering: prefer nearby/
broader roles over an empty result set).
"""

from __future__ import annotations

from typing import Callable

from jobedge.config import Config

MIN_RESULTS_BEFORE_RELAX = 5

SearchFn = Callable[[str | None, str], list[dict]]


def search_all_locations(config: Config, source_name: str, search: SearchFn) -> list[dict]:
    keyword_variants = _keyword_variants(config)
    seen_urls: set[str] = set()
    all_rows: list[dict] = []
    failed_cities: list[str] = []

    for location in config.target_locations:
        city = location["city"]
        try:
            city_rows: list[dict] = []
            for keywords in keyword_variants:
                city_rows.extend(search(keywords, city))
            if len(city_rows) < MIN_RESULTS_BEFORE_RELAX:
                print(
                    f"  {source_name}: only {len(city_rows)} for '{city}' across "
                    f"{len(keyword_variants)} title(s), relaxing to city-only search"
                )
                city_rows = search(None, city)
        except Exception as exc:
            failed_cities.append(city)
            print(f"  {source_name}: request failed for '{city}': {exc}")
            continue

        for row in city_rows:
            if row["url"] and row["url"] not in seen_urls:
                seen_urls.add(row["url"])
                all_rows.append(row)

    # Every location erroring means the source itself is unreachable/blocked
    # -- that must surface as a failure, never as a quiet "0 jobs today".
    if failed_cities and len(failed_cities) == len(config.target_locations):
        raise RuntimeError(f"{source_name}: every location failed, likely blocked or unreachable")

    print(f"  {source_name}: {len(all_rows)} unique listings across {len(config.target_locations)} locations")
    return all_rows


def _keyword_variants(config: Config) -> list[str]:
    """One search phrase per profile target title, searched separately --
    never concatenated into one literal compound phrase, which matches
    nothing (confirmed via eluta.ca's own "no results for <the entire
    concatenated string>" message, with job_bank showing the identical
    always-relax symptom)."""
    variants: list[str] = []
    seen: set[str] = set()
    for profile in config.profiles:
        for title in profile.target_titles:
            if title not in seen:
                seen.add(title)
                variants.append(title)
    return variants
