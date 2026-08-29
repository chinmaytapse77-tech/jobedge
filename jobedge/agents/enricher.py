"""Description enricher: fetches the real job description for the
highest-scoring listings from the cheap title-only Scorer pass, then
rescores just those rows with the richer text. Bounded to a small top-N
so this respects rate limits (steering rule 15) -- fetching every
listing's own page would be a much heavier hit on the source than the
search-results-only pass, and most listings never get a decent title
match anyway.
"""

from __future__ import annotations

import time

from jobedge.agents.base import Agent, AgentResult
from jobedge.config import Config, find_profile
from jobedge.scoring import pick_track, score_listing
from jobedge.sources.eluta import fetch_description as fetch_eluta_description
from jobedge.sources.job_bank import fetch_description as fetch_job_bank_description
from jobedge.storage import get_enrichment_candidates, update_listing_description, update_listing_score

MIN_SCORE_TO_ENRICH = 30
MAX_CANDIDATES = 30

_FETCHERS = {"job_bank": fetch_job_bank_description, "eluta": fetch_eluta_description}


class Enricher(Agent):
    name = "enricher"

    def run(self, config: Config, db_path: str) -> AgentResult:
        candidates = get_enrichment_candidates(db_path, MIN_SCORE_TO_ENRICH, MAX_CANDIDATES)
        if not candidates:
            return AgentResult(agent=self.name, status="ok", records_touched=0, notes="no candidates to enrich")

        sales_profile = find_profile(config, "sales")
        hr_profile = find_profile(config, "hr")
        enriched = 0
        skipped = 0

        for listing in candidates:
            fetcher = _FETCHERS.get(listing["source"])
            if fetcher is None:
                skipped += 1
                continue

            time.sleep(config.request_delay_seconds)
            try:
                description, posted_at = fetcher(listing["url"])
            except Exception as exc:  # one bad detail page must not kill enrichment
                print(f"  enricher: failed to fetch description for {listing['url']}: {exc}")
                continue
            if not description:
                continue

            update_listing_description(db_path, listing["id"], description, posted_at)
            sales_score, sales_reason = score_listing(
                sales_profile, listing["title"], description, listing["location"]
            )
            hr_score, hr_reason = score_listing(hr_profile, listing["title"], description, listing["location"])
            best_track = pick_track(sales_score, hr_score)
            update_listing_score(
                db_path, listing["id"], sales_score, sales_reason, hr_score, hr_reason, best_track
            )
            enriched += 1

        notes = f"enriched {enriched}/{len(candidates)} candidates with real descriptions"
        if skipped:
            notes += f" ({skipped} skipped, no fetcher for that source)"
        return AgentResult(agent=self.name, status="ok", records_touched=enriched, notes=notes)
