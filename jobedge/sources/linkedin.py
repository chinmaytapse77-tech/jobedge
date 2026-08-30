"""LinkedIn public job search -- logged out only, slow rate, NEVER an
authenticated session (steering rule, non-negotiable). Uses LinkedIn's own
"guest" search endpoint (the one linkedin.com/jobs/search itself calls for
pagination on the public page) -- no cookies, no login, just a plain GET,
so it stays within "public job search pages, logged out only".

LinkedIn fights automated traffic hard; selectors below are a best-effort
first guess like Indeed's. A one-time debug dump fires on anything
unexpected so the real markup (or a block/CAPTCHA page) can be captured
from a live run and fixed from there.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jobedge.config import Config
from jobedge.sources.base import Source, normalize_row, register
from jobedge.sources.dateparse import parse_posted_at
from jobedge.sources.http import get_html
from jobedge.sources.util import search_all_locations

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
MAX_PAGES = 3
RESULTS_PER_PAGE = 25

_debug_no_cards_printed = False
_debug_card_printed = False
_debug_date_printed = False


@register
class LinkedInSource(Source):
    name = "linkedin"

    def fetch(self, config: Config) -> list[dict]:
        return search_all_locations(config, self.name, _search)


def _search(keywords: str | None, city: str) -> list[dict]:
    """Raises on request failure -- search_all_locations decides whether
    that's a one-location blip or the whole source being unreachable."""
    rows: list[dict] = []
    for page in range(MAX_PAGES):
        params = {"location": city, "start": page * RESULTS_PER_PAGE}
        if keywords:
            params["keywords"] = keywords
        html = get_html(SEARCH_URL, params=params)
        page_rows = _parse(html)
        if not page_rows:
            break
        rows.extend(page_rows)
    return rows


def _parse(html: str) -> list[dict]:
    global _debug_no_cards_printed, _debug_card_printed, _debug_date_printed
    soup = BeautifulSoup(html, "html.parser")
    # The <a class="base-card__full-link"> is a SIBLING of div.base-card, not
    # nested inside it -- <li> is the smallest container holding both.
    cards = soup.select("li") or soup.select("div.base-card")
    if not cards and not _debug_no_cards_printed:
        print(f"  linkedin: DEBUG zero result cards -- first 2000 chars of page:\n{html[:2000]}")
        _debug_no_cards_printed = True

    rows = []
    for card in cards:
        link = card.select_one("a.base-card__full-link") or card.find("a", href=True)
        title_el = card.select_one("h3.base-search-card__title")
        if link is None or title_el is None:
            continue
        url = link.get("href", "").split("?")[0]
        title = title_el.get_text(strip=True) or None
        company_el = card.select_one("h4.base-search-card__subtitle")
        location_el = card.select_one(".job-search-card__location")
        if (not company_el or not location_el) and not _debug_card_printed:
            print(f"  linkedin: DEBUG full card HTML (company/location selectors unverified):\n{str(card)[:2000]}")
            _debug_card_printed = True

        time_el = card.select_one("time.job-search-card__listdate, time")
        posted_at = parse_posted_at(time_el.get("datetime") if time_el else None)
        if posted_at is None:
            posted_at = parse_posted_at(card.get_text(" ", strip=True))
        if posted_at is None and not _debug_date_printed:
            print(f"  linkedin: DEBUG couldn't find a posting date in card text:\n{card.get_text(' ', strip=True)[:500]}")
            _debug_date_printed = True

        rows.append(
            normalize_row(
                source="linkedin",
                external_id=url,
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
        print("  linkedin: found result cards but couldn't extract a link/title from any — selectors are stale")
    return rows
