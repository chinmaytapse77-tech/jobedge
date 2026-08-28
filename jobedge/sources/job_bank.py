"""Job Bank (jobbank.gc.ca) — public search results. No signup, no key, free.

Verified against real markup (captured via a one-time debug dump from a
live Actions run): search-result cards are <a class="resultJobItem"> with
an inner <h3 class="title"> that wraps BOTH the badge/status spans (New,
Direct Apply, "Posted on Job Bank...") AND a separate <span class="noctitle">
holding just the real title. `select_one(".noctitle, h3, h4")` doesn't
prefer .noctitle -- BeautifulSoup returns the first match in *document
order*, and the wrapping <h3> comes first, so it always won that lookup.
That's the actual cause of the earlier corrupted-title bug.

The search-results list page has NO description/summary text at all --
only an individual job posting's own page does (fetch_description below).
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from jobedge.config import Config
from jobedge.sources.base import Source, normalize_row, register
from jobedge.sources.http import get_html
from jobedge.sources.util import search_all_locations

SEARCH_URL = "https://www.jobbank.gc.ca/jobsearch/jobsearch"
MAX_PAGES = 3
MAX_DESCRIPTION_CHARS = 4000

_debug_detail_printed = False


@register
class JobBankSource(Source):
    name = "job_bank"

    def fetch(self, config: Config) -> list[dict]:
        return search_all_locations(config, self.name, _search)


def _search(keywords: str | None, city: str) -> list[dict]:
    """Raises on request failure -- search_all_locations decides whether
    that's a one-location blip or the whole source being unreachable."""
    rows: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        params = {"locationstring": city, "page": page}
        if keywords:
            params["searchstring"] = keywords
        html = get_html(SEARCH_URL, params=params)
        page_rows = _parse(html)
        if not page_rows:
            break
        rows.extend(page_rows)
    return rows


def _parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = (
        soup.select("article.resultJobItem")
        or soup.select("div.resultJobItem")
        or soup.select("a[href*='/jobsearch/jobposting/']")
    )
    rows = []
    for card in cards:
        link = card if card.name == "a" else card.select_one("a[href*='/jobsearch/jobposting/']")
        if link is None:
            continue
        href = link.get("href", "")
        url = href if href.startswith("http") else f"https://www.jobbank.gc.ca{href}"
        external_id = href.rstrip("/").split("/")[-1] or url
        title_el = card.select_one(".noctitle") or card.select_one("h3, h4") or link
        company_el = card.select_one(".business")
        location_el = card.select_one(".location")
        rows.append(
            normalize_row(
                source="job_bank",
                external_id=external_id,
                title=strip_label(title_el.get_text(strip=True) if title_el else None, "Job Bank"),
                company=company_el.get_text(strip=True) if company_el else None,
                location=strip_label(location_el.get_text(strip=True) if location_el else None, "Location"),
                url=url,
                description=None,
                posted_at=None,
                raw=str(card)[:2000],
            )
        )
    if cards and not rows:
        print("  job_bank: found result cards but couldn't extract a URL from any — selectors are stale")
    return rows


def fetch_description(url: str) -> str | None:
    """Fetch one job posting's own page and pull its main content text.
    Job Bank runs the Government of Canada WET template (confirmed by the
    wb-inv visually-hidden-text convention seen in list-page markup), whose
    main content lives in <main>; falls back to <body> if that's missing."""
    global _debug_detail_printed
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main") or soup.body
    if main is None:
        return None
    text = main.get_text(" ", strip=True)
    if not _debug_detail_printed:
        print(f"  job_bank: DEBUG detail page main content (first 1500 chars):\n{text[:1500]}")
        _debug_detail_printed = True
    return text[:MAX_DESCRIPTION_CHARS] or None


def strip_label(text: str | None, label: str) -> str | None:
    """Defensive backstop for the h3/h4 fallback path: if that's ever hit,
    badge/status text is still glued onto the front with no separator, and
    the real value reliably starts right after the last occurrence of the
    trailing label."""
    if not text:
        return text
    if label in text:
        text = text.rsplit(label, 1)[-1]
    return text.strip() or None
