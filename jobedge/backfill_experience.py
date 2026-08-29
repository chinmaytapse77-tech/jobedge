"""One-off backfill: computes experience_ok for rows scored before that
column existed. Safe to run any time -- already-classified rows are left
untouched.

python -m jobedge.backfill_experience
"""

from __future__ import annotations

from jobedge.config import load_config
from jobedge.experience import is_within_experience_range
from jobedge.storage import backfill_experience_ok


def main() -> None:
    config = load_config()
    updated = backfill_experience_ok(config.db_path, config.max_years_experience, is_within_experience_range)
    print(f"backfilled {updated} listing(s)")


if __name__ == "__main__":
    main()
