"""Adapts a real Source into the Agent interface.

This is the isolation boundary for steering rule 13: whatever a Source
raises (network error, parsing error, anything) is caught here and turned
into a "failed" AgentResult — it never propagates up and kills the cycle.
"""

from __future__ import annotations

from jobedge.agents.base import Agent, AgentResult
from jobedge.config import Config
from jobedge.sources.base import Source
from jobedge.storage import make_listing_id, upsert_listings, utcnow_iso


class SourceFetcher(Agent):
    def __init__(self, source: Source):
        self.source = source
        self.name = source.name

    def run(self, config: Config, db_path: str) -> AgentResult:
        try:
            raw_rows = self.source.fetch(config)
        except Exception as exc:  # a dead source must never kill the cycle
            return AgentResult(
                agent=self.name, status="failed", records_touched=0,
                notes=f"source raised: {exc}",
            )

        rows = [self._to_listing_row(row) for row in raw_rows]
        new_count = upsert_listings(db_path, rows)
        return AgentResult(
            agent=self.name,
            status="ok",
            records_touched=new_count,
            notes=f"{len(rows)} rows ({new_count} new)",
        )

    def _to_listing_row(self, row: dict) -> dict:
        return {
            "id": make_listing_id(row["source"], row["url"]),
            "title": row["title"],
            "company": row["company"],
            "location": row["location"],
            "url": row["url"],
            "description": row["description"],
            "source": row["source"],
            "posted_at": row["posted_at"],
            "fetched_at": utcnow_iso(),
        }
