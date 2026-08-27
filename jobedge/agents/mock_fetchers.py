"""Mock fetchers standing in for real scraping sources.

Job Bank, Jobillico, and Talent.com get real fetchers first (Prompt 4); these
four give the orchestrator something to run end-to-end today. Listings are
fixed (same title/company/url per source/seq) so ids are stable across runs
and dedup can be proven.
"""

from __future__ import annotations

from jobedge.agents.base import Agent, AgentResult
from jobedge.config import Config
from jobedge.storage import make_listing_id, upsert_listings, utcnow_iso

_SALES_SKILLS = "B2B sales, SaaS, CRM, consultative selling, quota attainment"
_HR_SKILLS = "HRIS, onboarding, compliance, Workday, payroll administration"

# (title, company, location, skills_blurb) x4 per source.
_FIXTURES: dict[str, list[tuple[str, str, str, str]]] = {
    "company_pages": [
        ("B2B Sales Executive", "Northline SaaS", "North York, ON", _SALES_SKILLS),
        ("HR Coordinator", "Northline SaaS", "North York, ON", _HR_SKILLS),
        ("Account Executive", "Vertex HRIS", "Toronto, ON", _SALES_SKILLS),
        ("HR Generalist", "Vertex HRIS", "Toronto, ON", _HR_SKILLS),
    ],
    "eluta": [
        ("Business Development Representative", "Cloudline Inc.", "North York, ON", _SALES_SKILLS),
        ("HR Administrative Assistant", "Cloudline Inc.", "North York, ON", _HR_SKILLS),
        ("Territory Sales Manager", "Prairie Tech", "Calgary, AB", _SALES_SKILLS),
        ("Recruitment Coordinator", "Prairie Tech", "Calgary, AB", _HR_SKILLS),
    ],
    "indeed": [
        ("Inside Sales Representative", "Maple Software", "Toronto, ON", _SALES_SKILLS),
        ("HR Assistant", "Maple Software", "Toronto, ON", _HR_SKILLS),
        ("Sales Representative", "Groupe Solutions QC", "Montreal, QC", _SALES_SKILLS),
        ("Adjoint Administratif", "Groupe Solutions QC", "Montreal, QC", _HR_SKILLS),
    ],
    "linkedin": [
        ("Account Executive", "SignalStack", "North York, ON", _SALES_SKILLS),
        ("Onboarding Coordinator", "SignalStack", "North York, ON", _HR_SKILLS),
        ("B2B Sales Executive", "Alberta Digital Co.", "Calgary, AB", _SALES_SKILLS),
        ("Global Mobility Analyst", "Alberta Digital Co.", "Calgary, AB", _HR_SKILLS),
    ],
}


def _build_listings(source: str) -> list[dict]:
    listings = []
    for seq, (title, company, location, skills) in enumerate(_FIXTURES[source], start=1):
        url = f"https://example-{source}.test/jobs/{seq}"
        listings.append(
            {
                "id": make_listing_id(source, url),
                "title": title,
                "company": company,
                "location": location,
                "url": url,
                "description": f"Ideal candidate has experience with: {skills}.",
                "source": source,
                "posted_at": "2026-08-20",
                "fetched_at": utcnow_iso(),
            }
        )
    return listings


class MockFetcher(Agent):
    """Returns 4 realistic, stable-id fake listings for one source."""

    def __init__(self, source: str):
        self.name = source

    def run(self, config: Config, db_path: str) -> AgentResult:
        listings = _build_listings(self.name)
        new_count = upsert_listings(db_path, listings)
        return AgentResult(
            agent=self.name,
            status="ok",
            records_touched=new_count,
            notes=f"{len(listings)} fetched, {new_count} new",
        )
