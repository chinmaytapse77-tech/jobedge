"""Eluta.ca — public search results, tolerant of light scraping. No key, free.

Connects fine (TLS handshake fixed in http.py), but none of the guessed
card selectors below have matched real markup yet -- this sandbox cannot
reach eluta.ca to verify directly. A one-time debug dump of the raw page
body fires on the next real run when zero cards match, so the actual
selector gets fixed from real structure instead of another guess.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jobedge.config import Config
from jobedge.sources.base import Source, normalize_row, register
from jobedge.sources.http import get_html
from jobedge.sources.util import search_all_locations

SEARCH_URL = "https://www.eluta.ca/search"
MAX_PAGES = 3

_debug_page_printed = False


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
    global _debug_page_printed
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("span.organic-job") or soup.select("li.organic-job") or soup.select("div.result")
    if not cards and not _debug_page_printed:
        _debug_scan(soup)
        _debug_page_printed = True
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


def _debug_scan(soup: BeautifulSoup) -> None:
    """The last debug dump (raw body, first 3000 chars) never reached the
    results section -- it's a big page and got truncated in the search
    form. Scanning for id/class mentioning "result" or "job" is a much
    smaller, more targeted signal than dumping more raw HTML blind."""
    matches = [
        el
        for el in soup.find_all(True)
        if (el.get("id") and any(t in el.get("id", "").lower() for t in ("result", "job")))
        or any(t in cls.lower() for cls in (el.get("class") or []) for t in ("result", "job"))
    ]
    print(f"  eluta: DEBUG no cards matched. Total tags on page: {len(soup.find_all(True))}")
    print(f"  eluta: DEBUG {len(matches)} tag(s) with 'result'/'job' in id or class (first 40):")
    for el in matches[:40]:
        print(f"    <{el.name} id={el.get('id')!r} class={el.get('class')!r}>")
    if not matches:
        print(f"  eluta: DEBUG no matches -- raw body (first 4000 chars):\n{str(soup.body)[:4000]}")
