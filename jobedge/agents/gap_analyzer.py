"""GapAnalyzer agent: per profile, ranks which missing skills would
unlock the most below-threshold listings if the candidate had them.
Runs once per cycle, after Scorer/Enricher.
"""

from __future__ import annotations

from jobedge.agents.base import Agent, AgentResult
from jobedge.config import Config, find_profile
from jobedge.gap_analysis import rank_skill_gaps
from jobedge.storage import get_scored_listings_below_threshold, replace_skill_gaps

_TRACKS = ("sales", "hr")


class GapAnalyzer(Agent):
    name = "gap_analyzer"

    def run(self, config: Config, db_path: str) -> AgentResult:
        summaries = []
        total_gaps = 0

        for profile_name in _TRACKS:
            profile = find_profile(config, profile_name)
            below = get_scored_listings_below_threshold(db_path, profile_name, config.min_fit_score)
            gaps = rank_skill_gaps(profile, config.min_fit_score, below)
            replace_skill_gaps(db_path, profile_name, gaps)
            total_gaps += len(gaps)
            top = ", ".join(f"{skill} ({count})" for skill, count in gaps[:3])
            summaries.append(f"{profile_name}: {top or 'no gaps found'}")

        return AgentResult(agent=self.name, status="ok", records_touched=total_gaps, notes=" | ".join(summaries))
