"""One-off backfill: re-applies job_bank.py's current title/location
cleanup to rows stored before the selector fix landed. Safe to run any
time -- already-clean rows are left untouched.

python -m jobedge.backfill_titles
"""

from __future__ import annotations

from jobedge.config import load_config
from jobedge.sources.job_bank import strip_label
from jobedge.storage import backfill_job_bank_text


def main() -> None:
    config = load_config()
    updated = backfill_job_bank_text(config.db_path, strip_label)
    print(f"backfilled {updated} listing(s)")


if __name__ == "__main__":
    main()
