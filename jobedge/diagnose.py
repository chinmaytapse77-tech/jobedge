"""Read-only diagnostic: python -m jobedge.diagnose

No writes, no schema changes — goes through the storage module only
(steering rule 2), never touches sqlite3 directly.
"""

from __future__ import annotations

from jobedge.config import load_config
from jobedge.storage import get_diagnostics


def main() -> None:
    config = load_config()
    summary = get_diagnostics(config.db_path)

    print(f"\nTotal listings: {summary['total']}")

    print("\nBy source:")
    for row in summary["by_source"]:
        print(f"  {row['source']:<16} {row['count']}")

    dupes = summary["cross_source_duplicates"]
    print(f"\nProbable cross-source duplicates (same title+company, different sources): {len(dupes)}")
    for row in dupes[:10]:
        print(f"  {row['title']} @ {row['company']} — {row['source_count']} sources")

    print("\n5 most recent listings:")
    for row in summary["recent"]:
        print(f"  [{row['source']}] {row['title']} @ {row['company']} ({row['fetched_at']})")

    issues = summary["quality_issues"]
    print(f"\nData quality issues (null/empty url, title, or company): {len(issues)}")
    for row in issues[:10]:
        print(f"  id={row['id']} source={row['source']} title={row['title']!r} "
              f"company={row['company']!r} url={row['url']!r}")
    print()


if __name__ == "__main__":
    main()
