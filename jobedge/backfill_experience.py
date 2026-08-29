"""One-off backfill: computes experience_ok for rows scored before that
column existed. Safe to run any time -- already-classified rows are left
untouched, unless FORCE_EXPERIENCE_BACKFILL=true (needed once whenever
config.max_years_experience itself changes, since an already-classified
row won't look missing to the normal pass).

python -m jobedge.backfill_experience
FORCE_EXPERIENCE_BACKFILL=true python -m jobedge.backfill_experience
"""

from __future__ import annotations

import os

from jobedge.config import load_config
from jobedge.experience import is_within_experience_range
from jobedge.storage import backfill_experience_ok


def main() -> None:
    config = load_config()
    force = os.environ.get("FORCE_EXPERIENCE_BACKFILL", "").lower() == "true"
    updated = backfill_experience_ok(
        config.db_path, config.max_years_experience, is_within_experience_range, force=force
    )
    print(f"backfilled {updated} listing(s){' (forced)' if force else ''}")


if __name__ == "__main__":
    main()
