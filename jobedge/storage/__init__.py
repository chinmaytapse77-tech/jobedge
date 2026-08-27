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
]
