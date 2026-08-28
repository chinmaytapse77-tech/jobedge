"""Scorer agent: scores every not-fully-scored listing against BOTH
profiles in one pass and sets best_track. Runs once per cycle (not once
per source) -- the orchestrator calls it directly after the fetch loop.
"""

from __future__ import annotations

from jobedge.agents.base import Agent, AgentResult
from jobedge.config import Config, find_profile
from jobedge.scoring import pick_track, score_listing
from jobedge.storage import get_unscored_listings, update_listing_score


class Scorer(Agent):
    name = "scorer"

    def run(self, config: Config, db_path: str) -> AgentResult:
        listings = get_unscored_listings(db_path)
        if not listings:
            return AgentResult(agent=self.name, status="ok", records_touched=0, notes="no unscored listings")

        sales_profile = find_profile(config, "sales")
        hr_profile = find_profile(config, "hr")
        track_counts = {"sales": 0, "hr": 0, None: 0}

        for listing in listings:
            sales_score, sales_reason = score_listing(
                sales_profile, listing["title"], listing["description"], listing["location"]
            )
            hr_score, hr_reason = score_listing(
                hr_profile, listing["title"], listing["description"], listing["location"]
            )
            best_track = pick_track(sales_score, hr_score)
            track_counts[best_track] += 1
            update_listing_score(
                db_path, listing["id"], sales_score, sales_reason, hr_score, hr_reason, best_track
            )

        notes = (
            f"scored {len(listings)} listings "
            f"(best_track: sales={track_counts['sales']}, hr={track_counts['hr']}, "
            f"none={track_counts[None]})"
        )
        return AgentResult(agent=self.name, status="ok", records_touched=len(listings), notes=notes)
