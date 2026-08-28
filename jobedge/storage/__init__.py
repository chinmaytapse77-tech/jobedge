"""SQLite storage layer for JobEdge.

The ONLY package allowed to import sqlite3 (steering rule 2). Every other
module calls the functions re-exported here — `from jobedge import storage`
— never `jobedge.storage._schema` / `_queries` directly.
"""

from jobedge.storage._queries import (
    count_unscored,
    get_diagnostics,
    get_listings,
    last_fetch_time,
    log_cycle,
    upsert_listings,
)
from jobedge.storage._schema import init_db, make_listing_id, utcnow_iso
from jobedge.storage._scoring import get_unscored_listings, update_listing_score
from jobedge.storage._enrichment import get_enrichment_candidates, update_listing_description
from jobedge.storage._gap_analysis import (
    get_scored_listings_below_threshold,
    get_skill_gaps,
    replace_skill_gaps,
)
from jobedge.storage._verification import get_all_scores, get_recent_agent_notes, reset_profile_scores
from jobedge.storage._maintenance import backfill_job_bank_text

__all__ = [
    "init_db",
    "make_listing_id",
    "utcnow_iso",
    "upsert_listings",
    "count_unscored",
    "last_fetch_time",
    "log_cycle",
    "get_listings",
    "get_diagnostics",
    "get_unscored_listings",
    "update_listing_score",
    "get_enrichment_candidates",
    "update_listing_description",
    "get_scored_listings_below_threshold",
    "replace_skill_gaps",
    "get_skill_gaps",
    "get_recent_agent_notes",
    "get_all_scores",
    "reset_profile_scores",
    "backfill_job_bank_text",
]
