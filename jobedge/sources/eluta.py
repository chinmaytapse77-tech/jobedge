"""Eluta.ca — public search results, tolerant of light scraping. No key, free.

UNVERIFIED against live markup, same caveat as job_bank.py: this sandbox
cannot reach eluta.ca. Verify locally; if 0 listings survive, the
selectors are stale — paste back one raw result card's HTML rather than
guessing at a fix.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jobedge.config import Config
from jobedge.sources.base import Source, normalize_row, register
from jobedge.sources.http import get_html
from jobedge.sources.util import search_all_locations

SEARCH_URL = "https://www.eluta.ca/search"
MAX_PAGES = 3


@register
class ElutaSource(Source):
    name = "eluta"

    def fetch(self, config: Config) -> list[dict]:
        return search_all_locations(config, self.name, _search)


def _search(keywords: str | None, city: str) -> list[dict]:
    """Raises on request failure -- search_all_locations decides whether
    that's a one-location blip or the whole source being unreachable."""
    rows: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        params = {"l": city, "pg": page}
        if keywords:
            params["q"] = keywords
        html = get_html(SEARCH_URL, params=params)
        page_rows = _parse(html)
        if not page_rows:
            break
        rows.extend(page_rows)
    return rows


def _parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("span.organic-job") or soup.select("li.organic-job") or soup.select("div.result")
    rows = []
    for card in cards:
        link = card.select_one("a.app-click-link") or card.find("a", href=True)
        if link is None:
            continue
        href = link.get("href", "")
        url = href if href.startswith("http") else f"https://www.eluta.ca{href}"
        title = link.get_text(strip=True) or None
        company_el = card.select_one(".orgName, .company")
        location_el = card.select_one(".location")
        rows.append(
            normalize_row(
                source="eluta",
                external_id=href,
                title=title,
                company=company_el.get_text(strip=True) if company_el else None,
                location=location_el.get_text(strip=True) if location_el else None,
                url=url,
                description=None,
                posted_at=None,
                raw=str(card)[:2000],
            )
        )
    if cards and not rows:
        print("  eluta: found result cards but couldn't extract a link from any — selectors are stale")
    return rows
