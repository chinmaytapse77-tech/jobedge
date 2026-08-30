"""Indeed (ca.indeed.com) -- public search results, logged out only, slow
rate (steering rule: Indeed/Monster/ZipRecruiter get the same caution as
each other). No key, free, but Indeed actively fights automated traffic
more than Job Bank or Eluta -- selectors below are a best-effort first
guess; a one-time debug dump fires on anything unexpected so the real
markup (or block page) can be captured from a live run and fixed from
there, same discipline used for Job Bank/Eluta.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jobedge.config import Config
from jobedge.sources.base import Source, normalize_row, register
from jobedge.sources.dateparse import parse_posted_at
from jobedge.sources.http import get_html
from jobedge.sources.util import search_all_locations

SEARCH_URL = "https://ca.indeed.com/jobs"
MAX_PAGES = 3
RESULTS_PER_PAGE = 10

_debug_no_cards_printed = False
_debug_card_printed = False
_debug_date_printed = False


@register
class IndeedSource(Source):
    name = "indeed"

    def fetch(self, config: Config) -> list[dict]:
        return search_all_locations(config, self.name, _search)


def _search(keywords: str | None, city: str) -> list[dict]:
    """Raises on request failure -- search_all_locations decides whether
    that's a one-location blip or the whole source being unreachable."""
    rows: list[dict] = []
    for page in range(MAX_PAGES):
        params = {"l": city, "start": page * RESULTS_PER_PAGE}
        if keywords:
            params["q"] = keywords
        html = get_html(SEARCH_URL, params=params)
        page_rows = _parse(html)
        if not page_rows:
            break
        rows.extend(page_rows)
    return rows


def _parse(html: str) -> list[dict]:
    global _debug_no_cards_printed, _debug_card_printed, _debug_date_printed
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.job_seen_beacon") or soup.select("td.resultContent")
    if not cards and not _debug_no_cards_printed:
        print(f"  indeed: DEBUG zero result cards -- first 2000 chars of page:\n{html[:2000]}")
        _debug_no_cards_printed = True

    rows = []
    for card in cards:
        link = card.select_one("h2.jobTitle a") or card.select_one("a.jcs-JobTitle")
        if link is None:
            continue
        job_key = link.get("data-jk")
        url = f"https://ca.indeed.com/viewjob?jk={job_key}" if job_key else link.get("href", "")
        title_el = link.select_one("span[title]") or link
        title = title_el.get_text(strip=True) or None
        company_el = card.select_one(".companyName")
        location_el = card.select_one(".companyLocation")
        if (not company_el or not location_el) and not _debug_card_printed:
            print(f"  indeed: DEBUG full card HTML (company/location selectors unverified):\n{str(card)[:2000]}")
            _debug_card_printed = True

        date_el = card.select_one(".date, [class*='date']")
        posted_at = parse_posted_at(date_el.get_text(" ", strip=True) if date_el else None)
        if posted_at is None:
            posted_at = parse_posted_at(card.get_text(" ", strip=True))
        if posted_at is None and not _debug_date_printed:
            print(f"  indeed: DEBUG couldn't find a posting date in card text:\n{card.get_text(' ', strip=True)[:500]}")
            _debug_date_printed = True

        rows.append(
            normalize_row(
                source="indeed",
                external_id=job_key or url,
                title=title,
                company=company_el.get_text(strip=True) if company_el else None,
                location=location_el.get_text(strip=True) if location_el else None,
                url=url,
                description=None,
                posted_at=posted_at,
                raw=str(card)[:2000],
            )
        )
    if cards and not rows:
        print("  indeed: found result cards but couldn't extract a link from any — selectors are stale")
    return rows
