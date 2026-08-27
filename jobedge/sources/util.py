"""Shared adaptive-search pattern for HTML-scraping Sources.

Searches every configured location; if a location+keyword combo returns
too few results, relaxes to a location-only search and logs that it did,
rather than silently returning a near-empty database (steering: prefer
nearby/broader roles over an empty result set).
"""

from __future__ import annotations

from typing import Callable

from jobedge.config import Config

MIN_RESULTS_BEFORE_RELAX = 5

SearchFn = Callable[[str | None, str], list[dict]]


def search_all_locations(config: Config, source_name: str, search: SearchFn) -> list[dict]:
    keywords = _combined_keywords(config)
    seen_urls: set[str] = set()
    all_rows: list[dict] = []
    failed_cities: list[str] = []

    for location in config.target_locations:
        city = location["city"]
        try:
            rows = search(keywords, city)
            if len(rows) < MIN_RESULTS_BEFORE_RELAX:
                print(f"  {source_name}: only {len(rows)} for '{city}' with keywords, relaxing to city-only search")
                rows = search(None, city)
        except Exception as exc:
            failed_cities.append(city)
            print(f"  {source_name}: request failed for '{city}': {exc}")
            continue

        for row in rows:
            if row["url"] and row["url"] not in seen_urls:
                seen_urls.add(row["url"])
                all_rows.append(row)

    # Every location erroring means the source itself is unreachable/blocked
    # -- that must surface as a failure, never as a quiet "0 jobs today".
    if failed_cities and len(failed_cities) == len(config.target_locations):
        raise RuntimeError(f"{source_name}: every location failed, likely blocked or unreachable")

    print(f"  {source_name}: {len(all_rows)} unique listings across {len(config.target_locations)} locations")
    return all_rows


def _combined_keywords(config: Config) -> str:
    titles: list[str] = []
    for profile in config.profiles:
        titles.extend(profile.target_titles[:2])
    seen: set[str] = set()
    unique = [t for t in titles if not (t in seen or seen.add(t))]
    return " ".join(unique)
