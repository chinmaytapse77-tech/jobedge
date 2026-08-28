"""Verifier agent: catches problems Fetchers/Scorer wouldn't catch on
their own -- a source silently returning zero rows instead of erroring,
or scoring collapsing toward the top of the range. Runs last, once per
cycle, and forces a fix rather than just logging a warning: a silently
blocked source gets one immediate retry; degenerate scoring gets reset
so the Scorer reprocesses everything next cycle.
"""

from __future__ import annotations

from jobedge.agents.base import Agent, AgentResult
from jobedge.config import Config
from jobedge.storage import get_all_scores, get_recent_agent_notes, reset_profile_scores
from jobedge.verification import is_scoring_degenerate, is_source_silent

_TRACKS = ("sales", "hr")


class Verifier(Agent):
    name = "verifier"

    def __init__(self, registry: dict, sources: list[str]):
        self.registry = registry
        self.sources = sources

    def run(self, config: Config, db_path: str) -> AgentResult:
        findings: list[str] = []

        for source in self.sources:
            if source not in self.registry:
                continue
            notes = get_recent_agent_notes(db_path, source, limit=2)
            if is_source_silent(notes):
                findings.append(f"{source}: likely blocked (0 rows on last {len(notes)} run(s)), retrying once")
                retry_result = self.registry[source]().run(config, db_path)
                findings.append(f"{source} retry: {retry_result.notes}")

        for profile_name in _TRACKS:
            scores = get_all_scores(db_path, profile_name)
            if is_scoring_degenerate(scores):
                reset_count = reset_profile_scores(db_path, profile_name)
                findings.append(f"{profile_name}: degenerate scoring detected, reset {reset_count} rows for rescore")

        notes = "; ".join(findings) if findings else "no issues found"
        status = "failed" if findings else "ok"
        return AgentResult(agent=self.name, status=status, records_touched=len(findings), notes=notes)
