"""Eluta.ca — public search results, tolerant of light scraping. No key, free.

Confirmed via a real debug scan: result cards live in #organic-jobs as
<div class="organic-job odd|even">, each with an <a class="lk-job-title">
title link. The earlier span.organic-job guess was one wrong tag name
(span vs div) away from working. Company/location selectors below are
still best-effort -- a one-time debug dump of a full real card fires if
a card is found but company/location can't be extracted, so those get
the same real-markup treatment if they're wrong too.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jobedge.config import Config
from jobedge.sources.base import Source, normalize_row, register
from jobedge.sources.http import get_html
from jobedge.sources.util import search_all_locations

SEARCH_URL = "https://www.eluta.ca/search"
MAX_PAGES = 3

_debug_no_cards_printed = False
_debug_card_printed = False


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
    global _debug_no_cards_printed, _debug_card_printed
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
        href = link.get("href", "")
        url = href if href.startswith("http") else f"https://www.eluta.ca{href}"
        title = link.get_text(strip=True) or None
        company_el = card.select_one(".orgName, .company, .lk-company")
        location_el = card.select_one(".location")
        if (not company_el or not location_el) and not _debug_card_printed:
            print(f"  eluta: DEBUG full card HTML (company/location selectors unverified):\n{str(card)[:2000]}")
            _debug_card_printed = True
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
