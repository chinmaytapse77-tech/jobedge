"""Eluta.ca — public search results, tolerant of light scraping. No key, free.

Confirmed via a real debug scan: result cards live in #organic-jobs as
<div class="organic-job odd|even">, each with an <a class="lk-job-title">
title link and an <a class="employer lk-employer"> for the company. The
title link's href is always a dead "#!" JS anchor -- the real destination
is its data-url attribute, which _resolve_url() uses instead (falling back
to href for any card that doesn't follow that pattern).
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jobedge.config import Config
from jobedge.sources.base import Source, normalize_row, register
from jobedge.sources.dateparse import parse_posted_at
from jobedge.sources.http import get_html
from jobedge.sources.util import search_all_locations

SEARCH_URL = "https://www.eluta.ca/search"
MAX_PAGES = 3

_debug_no_cards_printed = False
_debug_card_printed = False
_debug_date_printed = False
_debug_detail_printed = False


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
        page_rows = _parse(html, params)
        if not page_rows:
            break
        rows.extend(page_rows)
    return rows


def _parse(html: str, params: dict | None = None) -> list[dict]:
    global _debug_no_cards_printed, _debug_card_printed, _debug_date_printed
    soup = BeautifulSoup(html, "html.parser")
    cards = (
        soup.select("div.organic-job")
        or soup.select("span.organic-job")
        or soup.select("li.organic-job")
        or soup.select("div.result")
    )
    if not cards and not _debug_no_cards_printed:
        _debug_scan(soup, params)
        _debug_no_cards_printed = True

    rows = []
    for card in cards:
        link = card.select_one("a.lk-job-title") or card.select_one("a.app-click-link") or card.find("a", href=True)
        if link is None:
            continue
        url = _resolve_url(link)
        title = link.get_text(strip=True) or None
        company_el = card.select_one(".employer, .lk-employer, .orgName, .company, .lk-company")
        location_el = card.select_one(".location")
        if (not company_el or not location_el) and not _debug_card_printed:
            print(f"  eluta: DEBUG full card HTML (company/location selectors unverified):\n{str(card)[:2000]}")
            _debug_card_printed = True

        date_el = card.select_one(".date, .lastseen, .posted, [class*='date']")
        posted_at = parse_posted_at(date_el.get_text(" ", strip=True) if date_el else None)
        if posted_at is None:
            posted_at = parse_posted_at(card.get_text(" ", strip=True))
        if posted_at is None and not _debug_date_printed:
            print(f"  eluta: DEBUG couldn't find a posting date in card text:\n{card.get_text(' ', strip=True)[:500]}")
            _debug_date_printed = True

        rows.append(
            normalize_row(
                source="eluta",
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
        print("  eluta: found result cards but couldn't extract a link from any — selectors are stale")
    return rows


def _resolve_url(link) -> str:
    """The title link's real destination is a JS-driven data-url attribute
    (e.g. "spl/b2b-sales-...?imo=12"); href is always the dead "#!" anchor.
    Falls back to href for any card that doesn't follow that pattern."""
    data_url = link.get("data-url")
    if data_url:
        return f"https://www.eluta.ca/{data_url.lstrip('/')}"
    href = link.get("href", "")
    return href if href.startswith("http") else f"https://www.eluta.ca{href}"


def fetch_description(url: str) -> tuple[str | None, str | None]:
    """Search cards carry no date (confirmed via production debug output) --
    this detail page is the only place an Eluta listing can pick one up."""
    global _debug_detail_printed
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main") or soup.body
    if main is None:
        return None, None
    text = main.get_text(" ", strip=True)
    posted_at = parse_posted_at(text)
    if not _debug_detail_printed:
        print(f"  eluta: DEBUG detail page main content (first 1500 chars):\n{text[:1500]}")
        _debug_detail_printed = True
    return text[:4000] or None, posted_at


def _debug_scan(soup: BeautifulSoup, params: dict | None) -> None:
    """Fires only if zero cards match at all (shouldn't happen now that
    div.organic-job is confirmed, but kept as a safety net for a future
    markup change)."""
    print(f"  eluta: DEBUG params that produced zero results: {params}")
    no_results_el = soup.select_one(".noResults")
    if no_results_el is not None:
        print(f"  eluta: DEBUG noResults message text: {no_results_el.get_text(' ', strip=True)!r}")
    matches = [
        el
        for el in soup.find_all(True)
        if (el.get("id") and any(t in el.get("id", "").lower() for t in ("result", "job")))
        or any(t in cls.lower() for cls in (el.get("class") or []) for t in ("result", "job"))
    ]
    print(f"  eluta: DEBUG {len(matches)} tag(s) with 'result'/'job' in id or class (first 15):")
    for el in matches[:15]:
        print(f"    <{el.name} id={el.get('id')!r} class={el.get('class')!r}>")
